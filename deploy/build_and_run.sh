#!/usr/bin/env bash
# Build the Command Center UI and run the whole Superman Brain on ONE port.
# Run this on the Manus box. Serves at http://<host>:8000
set -euo pipefail

# Resolve repo locations (this script lives in goldfront-os/deploy/)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "$HERE/.." && pwd)"
UI_DIR="$(cd "$BRAIN_DIR/.." && pwd)/conrad-command-center"

echo "==> Brain:  $BRAIN_DIR"
echo "==> UI:     $UI_DIR"

# 1) Build the React UI (needs Node installed on the box)
if [ -d "$UI_DIR" ]; then
  echo "==> Building Command Center UI..."
  ( cd "$UI_DIR" && npm install && npm run build )
else
  echo "!! conrad-command-center not found next to goldfront-os — skipping UI build."
fi

# 2) Python env + deps
cd "$BRAIN_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

# 3) Run the whole thing on one port, reachable on the network.
#    GOLDFRONT_OWNER=lindsey keeps this as Lindsey's private brain.
export GOLDFRONT_OWNER="${GOLDFRONT_OWNER:-lindsey}"
echo "==> Serving Superman Brain at http://0.0.0.0:8000  (owner: $GOLDFRONT_OWNER)"
exec uvicorn brain.main:app --host 0.0.0.0 --port 8000
