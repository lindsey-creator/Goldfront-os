#!/usr/bin/env bash
# Run from Lindsey's Mac to push repos to Manus and trigger remote deploy.
# Prereq: your Mac SSH public key in ~/.ssh/authorized_keys on the Manus box.
set -euo pipefail

MANUS_HOST="${MANUS_HOST:-lindseyconrad@34.26.142.220}"
REMOTE_BASE="${REMOTE_BASE:-Documents/Claude/Projects/Brain}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GO="$ROOT/goldfront-os"
CC="$ROOT/conrad-command-center"

[ -d "$GO" ] && [ -d "$CC" ] || die() { echo "$*"; exit 1; }

RSYNC_EX=(
  --exclude '.git' --exclude 'node_modules' --exclude '.venv'
  --exclude '__pycache__' --exclude '.env' --exclude '.pytest_cache'
)

echo "==> Rsync to $MANUS_HOST"
rsync -avz "${RSYNC_EX[@]}" "$GO/" "$MANUS_HOST:~/$REMOTE_BASE/goldfront-os/"
rsync -avz "${RSYNC_EX[@]}" "$CC/" "$MANUS_HOST:~/$REMOTE_BASE/conrad-command-center/"

echo "==> Remote deploy"
ssh "$MANUS_HOST" "bash ~/$REMOTE_BASE/goldfront-os/deploy/FINISH_ON_MANUS.sh"

echo "==> Remote health"
ssh "$MANUS_HOST" "curl -sf http://127.0.0.1:8000/health; echo; curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool | head -30"
