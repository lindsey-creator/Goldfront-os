#!/usr/bin/env bash
# One-command setup on the Manus always-on machine (macOS or Linux).
# Run ON Manus after repos exist side by side under BRAIN_PARENT.
set -euo pipefail

BRAIN_PARENT="${BRAIN_PARENT:-$HOME/Documents/Claude/Projects/Brain}"
BRAIN_DIR="${BRAIN_DIR:-$BRAIN_PARENT/goldfront-os}"
UI_DIR="${UI_DIR:-$BRAIN_PARENT/conrad-command-center}"
GOLDFRONT_OWNER="${GOLDFRONT_OWNER:-lindsey}"
LOG_DIR="${LOG_DIR:-$HOME/Library/Logs/goldfront}"
SERVICE_NAME="com.goldfront.command-center"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { echo "ERROR: $*" >&2; exit 1; }

command -v python3 >/dev/null || die "Install Python 3.9+ first."
command -v node >/dev/null || die "Install Node.js 18+ first."
command -v npm >/dev/null || die "npm not found (install Node.js)."

[ -d "$BRAIN_DIR" ] || die "Brain repo missing: $BRAIN_DIR"
[ -f "$BRAIN_DIR/requirements.txt" ] || die "Not goldfront-os: $BRAIN_DIR"

echo "==> Brain: $BRAIN_DIR"
echo "==> UI:    $UI_DIR"

if [ -d "$UI_DIR" ]; then
  echo "==> Building Command Center UI…"
  (cd "$UI_DIR" && npm install && npm run build)
else
  echo "!! UI repo not found — API only until you clone conrad-command-center."
fi

echo "==> Python venv + deps…"
cd "$BRAIN_DIR"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -U pip
pip install -q -r requirements.txt

if [ ! -f "$BRAIN_DIR/.env" ] && [ -f "$BRAIN_DIR/.env.example" ]; then
  echo "==> No .env — copy .env.example and add keys when ready (not done automatically)."
fi

OS="$(uname -s)"
UVICORN="$BRAIN_DIR/.venv/bin/uvicorn"

install_macos() {
  mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"
  PLIST="$HOME/Library/LaunchAgents/${SERVICE_NAME}.plist"
  sed -e "s|__BRAIN_DIR__|$BRAIN_DIR|g" \
      -e "s|__UVICORN__|$UVICORN|g" \
      -e "s|__GOLDFRONT_OWNER__|$GOLDFRONT_OWNER|g" \
      -e "s|__LOG_DIR__|$LOG_DIR|g" \
      "$HERE/com.goldfront.command-center.plist.template" > "$PLIST"
  launchctl bootout "gui/$(id -u)/$SERVICE_NAME" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  launchctl enable "gui/$(id -u)/$SERVICE_NAME"
  echo "==> launchd: $PLIST (logs in $LOG_DIR)"
}

install_linux() {
  UNIT_SRC="$HERE/superman-brain.service.template"
  UNIT_DST="/etc/systemd/system/superman-brain.service"
  TMP="$(mktemp)"
  sed -e "s|__USER__|$(whoami)|g" \
      -e "s|__BRAIN_DIR__|$BRAIN_DIR|g" \
      -e "s|__GOLDFRONT_OWNER__|$GOLDFRONT_OWNER|g" \
      "$UNIT_SRC" > "$TMP"
  if [ -w /etc/systemd/system ]; then
    cp "$TMP" "$UNIT_DST"
  else
    echo "==> Need sudo to install systemd unit:"
    sudo cp "$TMP" "$UNIT_DST"
  fi
  rm -f "$TMP"
  sudo systemctl daemon-reload
  sudo systemctl enable --now superman-brain
  echo "==> systemd: superman-brain.service"
}

case "$OS" in
  Darwin) install_macos ;;
  Linux)  install_linux ;;
  *) die "Unsupported OS: $OS (use docker-compose.yml or run uvicorn manually)" ;;
esac

echo ""
echo "==> Command Center + Brain should be on http://0.0.0.0:8000"
echo "    Local:  http://127.0.0.1:8000"
echo "    LAN:    http://$(hostname -f 2>/dev/null || hostname):8000"
echo "    Owner:  $GOLDFRONT_OWNER"
