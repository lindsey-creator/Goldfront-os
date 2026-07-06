#!/usr/bin/env bash
# Run from your Mac when MANUS_SSH is configured (e.g. lindsey@manus.local).
set -euo pipefail

MANUS_SSH="${MANUS_SSH:-}"
REMOTE_BASE="${REMOTE_BASE:-Documents/Claude/Projects/Brain}"

if [ -z "$MANUS_SSH" ]; then
  echo "Set MANUS_SSH, e.g. export MANUS_SSH=lindsey@manus"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CC="$ROOT/conrad-command-center"
GO="$ROOT/goldfront-os"

[ -d "$CC" ] && [ -d "$GO" ] || { echo "Expected $ROOT/{goldfront-os,conrad-command-center}"; exit 1; }

RSYNC_EXCLUDES=(
  --exclude '.git'
  --exclude 'node_modules'
  --exclude '.venv'
  --exclude '__pycache__'
  --exclude '.env'
  --exclude '.pytest_cache'
  --exclude '*.pyc'
)

echo "==> Building UI locally…"
(cd "$CC" && npm run build)

REMOTE_GO="$MANUS_SSH:~/$REMOTE_BASE/goldfront-os/"
REMOTE_CC="$MANUS_SSH:~/$REMOTE_BASE/conrad-command-center/"

echo "==> Rsync to $MANUS_SSH"
rsync -avz "${RSYNC_EXCLUDES[@]}" "$GO/" "$REMOTE_GO"
rsync -avz "${RSYNC_EXCLUDES[@]}" "$CC/" "$REMOTE_CC"

echo "==> Install / restart on Manus…"
ssh "$MANUS_SSH" "bash ~/$REMOTE_BASE/goldfront-os/deploy/manus/install-on-manus.sh"

echo "==> Health check…"
ssh "$MANUS_SSH" "curl -sf -o /dev/null http://127.0.0.1:8000/docs && echo OK: http://127.0.0.1:8000"
