#!/usr/bin/env bash
# SettleFlow rollback — restore a previous deploy and prove it came back.
#
#   bash scripts/rollback.sh latest
#   bash scripts/rollback.sh 20260911-013045
#   bash scripts/rollback.sh --list
#
# The backup is code only (no .venv), taken by scripts/deploy.sh before it
# overwrote anything. A rollback path that has never been run is a guess, so this
# one is exercised in the session that wrote it and its output is recorded in
# docs/COMPLETION.md.
set -uo pipefail

_HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
[ -f "$_HERE/.deploy.env" ] && . "$_HERE/.deploy.env"

# Same rule as deploy.sh: the origin host is never hardcoded in this public repo.
HOST="${SETTLEFLOW_HOST:-}"
if [ -z "$HOST" ]; then
  echo "SETTLEFLOW_HOST is not set." >&2
  echo "  export SETTLEFLOW_HOST=root@your.server   (or create scripts/.deploy.env)" >&2
  exit 2
fi

REMOTE_DIR="${SETTLEFLOW_REMOTE_DIR:-/opt/settleflow}"
BACKUP_DIR="${REMOTE_DIR}-backups"
UNIT="${SETTLEFLOW_UNIT:-settleflow}"
LOCAL_PORT="${SETTLEFLOW_LOCAL_PORT:-8093}"

die() { printf '\nFAIL: %s\n' "$1" >&2; exit 1; }

if [ "${1:-}" = "--list" ] || [ -z "${1:-}" ]; then
  echo "available backups on $HOST:"
  ssh -o BatchMode=yes "$HOST" "ls -1t $BACKUP_DIR/*.tar.gz 2>/dev/null || echo '  (none)'"
  exit 0
fi

TARGET="$1"
if [ "$TARGET" = "latest" ]; then
  TARGET="$(ssh -o BatchMode=yes "$HOST" \
    "ls -1t $BACKUP_DIR/*.tar.gz 2>/dev/null | head -1 | xargs -r basename | sed 's/\.tar\.gz$//'")"
  [ -n "$TARGET" ] || die "no backups found in $BACKUP_DIR"
fi

echo "rolling back to $TARGET"
ssh -o BatchMode=yes "$HOST" "test -f $BACKUP_DIR/$TARGET.tar.gz" \
  || die "$BACKUP_DIR/$TARGET.tar.gz not found (use --list)"

# Take a backup of what is live right now, so a rollback is itself reversible.
NOW="$(ssh -o BatchMode=yes "$HOST" 'date -u +%Y%m%d-%H%M%S')"
ssh -o BatchMode=yes "$HOST" "
  set -e
  cd $REMOTE_DIR
  mkdir -p $BACKUP_DIR
  existing=''
  for p in settleflow saas scripts docs pyproject.toml; do
    [ -e \"\$p\" ] && existing=\"\$existing \$p\" || true
  done
  tar czf $BACKUP_DIR/pre-rollback-$NOW.tar.gz --exclude='__pycache__' --exclude='*.pyc' --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' --exclude='*.sqlite' --exclude='*.sqlite3' \$existing
  test -s $BACKUP_DIR/pre-rollback-$NOW.tar.gz
  tar xzf $BACKUP_DIR/$TARGET.tar.gz -C $REMOTE_DIR
  echo '  restored $TARGET (current state saved as pre-rollback-$NOW.tar.gz)'
" || die "restore failed"

echo "restarting $UNIT"
ssh -o BatchMode=yes "$HOST" "systemctl restart $UNIT"
sleep 2

HEALTH=""
for _ in $(seq 1 10); do
  HEALTH="$(ssh -o BatchMode=yes "$HOST" "curl -s -m 5 http://127.0.0.1:$LOCAL_PORT/health" || true)"
  case "$HEALTH" in *'"status":"ok"'*) break ;; esac
  sleep 2
done
case "$HEALTH" in
  *'"status":"ok"'*) echo "  health: $HEALTH" ;;
  *) ssh -o BatchMode=yes "$HOST" "journalctl -u $UNIT -n 40 --no-pager"
     die "rolled back but the service did not come up — the pre-rollback archive is $BACKUP_DIR/pre-rollback-$NOW.tar.gz" ;;
esac

echo "canary after rollback:"
# Validate with the NEWEST canary, not the copy inside the restored archive. Rolling
# the test tool back together with the app is how a drill passes while the release it
# restored is broken: the old release and the old canary share the same blind spot.
# The canary from the pre-rollback snapshot (i.e. what was live a moment ago) is the
# newest tool available, so it is the one that judges the restored code.
ssh -o BatchMode=yes "$HOST" "
  set -e
  if tar tzf $BACKUP_DIR/pre-rollback-$NOW.tar.gz scripts/canary.py >/dev/null 2>&1; then
    tar xzf $BACKUP_DIR/pre-rollback-$NOW.tar.gz -O scripts/canary.py > /tmp/settleflow-canary-current.py
    cd $REMOTE_DIR && .venv/bin/python /tmp/settleflow-canary-current.py --base http://127.0.0.1:$LOCAL_PORT
  else
    echo '  (no newer canary in the pre-rollback snapshot; using the restored one)'
    cd $REMOTE_DIR && .venv/bin/python scripts/canary.py --base http://127.0.0.1:$LOCAL_PORT
  fi
" || die "rolled back, but the newest canary fails against the restored release — this backup is not a good target; the pre-rollback archive is $BACKUP_DIR/pre-rollback-$NOW.tar.gz"

echo
echo "rollback to $TARGET complete and verified"
