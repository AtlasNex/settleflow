#!/usr/bin/env bash
# SettleFlow deploy — idempotent, and it fails loudly.
#
#   bash scripts/deploy.sh                 # ship + restart + verify
#   bash scripts/deploy.sh --deps          # also reinstall the [saas] extra
#   bash scripts/deploy.sh --skip-backup   # (only if you just made one)
#
# Why this exists: every deploy before it was hand-typed scp + systemctl, so the
# thing that actually ran on the box was whatever someone's shell history said.
#
# Properties this script guarantees:
#  - refuses to ship if the local self-check is not green
#  - backs up the previous code on the server first, and prints how to roll back
#  - assert-after-restart: /health must answer, AND the end-to-end canary must
#    pass (a process that is up but not reconciling is the failure mode a plain
#    health check cannot see)
#  - asserts the public URL from OUTSIDE as well as loopback
#
# Deployment shape (D-28): this VPS is a Proxmox LXC with no AppArmor, so
# `docker compose build` fails. The service runs host-run under systemd from
# /opt/settleflow, and the .venv lives there and must survive a deploy — which is
# why this ships an allowlist of paths rather than mirroring the repo tree.
#
# The host is NOT hardcoded. This repository is public and the origin IP is not in
# public DNS (Cloudflare proxies it), so committing the address would hand out a
# direct route that bypasses the Cloudflare Access rules on this origin. Set it in
# the environment, or in the gitignored scripts/.deploy.env.
set -uo pipefail

_HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[ -f "$_HERE/.deploy.env" ] && . "$_HERE/.deploy.env"

HOST="${SETTLEFLOW_HOST:-}"

REMOTE_DIR="${SETTLEFLOW_REMOTE_DIR:-/opt/settleflow}"
BACKUP_DIR="${REMOTE_DIR}-backups"
UNIT="${SETTLEFLOW_UNIT:-settleflow}"
PUBLIC_BASE="${SETTLEFLOW_PUBLIC_BASE:-https://settleflow.atlasnex.com}"
LOCAL_PORT="${SETTLEFLOW_LOCAL_PORT:-8093}"
KEEP_BACKUPS=5

DEPS=0
SKIP_BACKUP=0
for arg in "$@"; do
  case "$arg" in
    --deps) DEPS=1 ;;
    --skip-backup) SKIP_BACKUP=1 ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

# Checked after --help so the usage text works on a machine with no target set.
if [ -z "$HOST" ]; then
  echo "SETTLEFLOW_HOST is not set." >&2
  echo "  export SETTLEFLOW_HOST=root@your.server   (or create scripts/.deploy.env)" >&2
  exit 2
fi

step() { printf '\n== %s\n' "$1"; }
die()  { printf '\nFAIL: %s\n' "$1" >&2; exit 1; }

# Files that must never be shipped. An explicit allowlist, not a mirror, because
# a mirror would carry research scratch and a stray sqlite db onto the box.
SHIP=(settleflow saas scripts docs/legal tests pyproject.toml README.md LICENSE)
# Files removed from the app but still present on the server from older deploys.
# tar cannot delete, so regressions caused by a deleted file have to be named here.
REMOVED=(saas/templates/runs.html)

cd "$(dirname "$0")/.." || die "cannot cd to repo root"
REPO="$PWD"

step "preflight: local self-check"
if ! python tests/test_matching.py > /tmp/settleflow-selfcheck.log 2>&1; then
  tail -20 /tmp/settleflow-selfcheck.log
  die "self-check is not green — refusing to deploy"
fi
tail -1 /tmp/settleflow-selfcheck.log

step "preflight: server reachable"
ssh -o BatchMode=yes -o ConnectTimeout=15 "$HOST" "test -d $REMOTE_DIR" \
  || die "cannot reach $HOST or $REMOTE_DIR does not exist"

REV="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
TS="$(ssh -o BatchMode=yes "$HOST" 'date -u +%Y%m%d-%H%M%S')"
echo "shipping revision $REV at $TS"

if [ "$SKIP_BACKUP" -eq 0 ]; then
  step "backup: previous code on the server (code only — the .venv is not copied)"
  # No `|| true` on the tar and an explicit `test -s`: a backup step that can pass
  # while producing an empty archive is worse than no backup, because it makes the
  # rollback path look available when it is not.
  >&2 ssh -o BatchMode=yes "$HOST" "
    set -e
    mkdir -p $BACKUP_DIR
    cd $REMOTE_DIR
    existing=''
    for p in settleflow saas scripts docs pyproject.toml; do
      [ -e \"\$p\" ] && existing=\"\$existing \$p\" || true
    done
    test -n \"\$existing\"
    tar czf $BACKUP_DIR/$TS.tar.gz --exclude='__pycache__' --exclude='*.pyc' \$existing
    test -s $BACKUP_DIR/$TS.tar.gz
    ls -1t $BACKUP_DIR/*.tar.gz | tail -n +$((KEEP_BACKUPS+1)) | xargs -r rm -f
    echo \"  backup: $BACKUP_DIR/$TS.tar.gz (\$(du -h $BACKUP_DIR/$TS.tar.gz | cut -f1)), contains:\$existing\"
  " || die "backup failed — refusing to deploy without a way back"
fi

step "ship: $REV"
for f in "${REMOVED[@]}"; do
  >&2 ssh -o BatchMode=yes "$HOST" "rm -f $REMOTE_DIR/$f"
done
tar czf - --exclude='__pycache__' --exclude='*.pyc' "${SHIP[@]}" \
  | ssh -o BatchMode=yes "$HOST" "tar xzf - -C $REMOTE_DIR" \
  || die "file transfer failed"

if [ "$DEPS" -eq 1 ]; then
  step "deps: reinstall the saas/pdf/ocr extras into the server venv"
  >&2 ssh -o BatchMode=yes "$HOST" \
    "cd $REMOTE_DIR && .venv/bin/pip install -q -e '.[saas,pdf,ocr]'" \
    || die "dependency install failed"
fi

step "restart $UNIT"
>&2 ssh -o BatchMode=yes "$HOST" "systemctl restart $UNIT"
sleep 2
>&2 ssh -o BatchMode=yes "$HOST" "systemctl is-active --quiet $UNIT" \
  || { >&2 ssh -o BatchMode=yes "$HOST" "journalctl -u $UNIT -n 40 --no-pager"; \
       die "$UNIT is not active after restart"; }
echo "$UNIT is active"

step "verify: /health on loopback (up to 20s)"
HEALTH=""
for _ in $(seq 1 10); do
  HEALTH="$(ssh -o BatchMode=yes "$HOST" "curl -s -m 5 http://127.0.0.1:$LOCAL_PORT/health" || true)"
  case "$HEALTH" in *'"status":"ok"'*) break ;; esac
  sleep 2
done
case "$HEALTH" in
  *'"status":"ok"'*) echo "  $HEALTH" ;;
  *) >&2 ssh -o BatchMode=yes "$HOST" "journalctl -u $UNIT -n 40 --no-pager"
     die "health check never came up — roll back with: bash scripts/rollback.sh $TS" ;;
esac

step "verify: end-to-end canary on the server (real reconcile round-trip)"
if ! ssh -o BatchMode=yes "$HOST" \
     "cd $REMOTE_DIR && .venv/bin/python scripts/canary.py --base http://127.0.0.1:$LOCAL_PORT" ; then
  die "canary FAILED — the service is up but not reconciling. Roll back with: bash scripts/rollback.sh $TS"
fi

step "verify: the public URL from outside the VPS"
OUT="$(curl -s -o /dev/null -w '%{http_code}' -m 25 "$PUBLIC_BASE/")"
HEALTH_PUB="$(curl -s -o /dev/null -w '%{http_code}' -m 25 "$PUBLIC_BASE/health")"
echo "  $PUBLIC_BASE/ -> $OUT ; /health -> $HEALTH_PUB"
[ "$OUT" = "200" ] || die "public root returned $OUT"
[ "$HEALTH_PUB" = "200" ] || die "public /health returned $HEALTH_PUB"

step "done"
cat <<EOF
revision shipped : $REV
backup on server : $BACKUP_DIR/$TS.tar.gz
rollback         : bash scripts/rollback.sh $TS
EOF
