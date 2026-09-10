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

HOST="${SETTLEFLOW_HOST:-root@13.140.59.39}"
REMOTE_DIR="${SETTLEFLOW_REMOTE_DIR:-/opt/settleflow}"
BACKUP_DIR="${REMOTE_DIR}-backups"
UNIT="${SETTLEFLOW_UNIT:-settleflow}"
LOCAL_PORT="${SETTLEFLOW_LOCAL_PORT:-8093}"

die() { printf '\nFAIL: %s\n' "$1" >&2; exit 1; }

if [ "${1:-}" = "--list" ] || [ -z "${1:-}" ]; then
  echo "available backups on $HOST:"
  ssh -o BatchMode=yes "$HOST" "ls -1t $BACKUP_DIR/*.tar.gz 2>/dev/null || echo '  (none)'"
  [ -n "${1:-}" ] || exit 0
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
  tar czf $BACKUP_DIR/pre-rollback-$NOW.tar.gz --exclude='__pycache__' --exclude='*.pyc' \$existing
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
ssh -o BatchMode=yes "$HOST" \
  "cd $REMOTE_DIR && .venv/bin/python scripts/canary.py --base http://127.0.0.1:$LOCAL_PORT" \
  || die "rolled back but the canary fails — service is up and not reconciling"

echo
echo "rollback to $TARGET complete and verified"
