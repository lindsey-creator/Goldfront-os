#!/usr/bin/env bash
# Paste/run ON the Manus Ubuntu box (command.theconradteam.com host).
# Pulls connector keys from /var/www/dashboard/.env → goldfront-os/.env, then deploys.
set -euo pipefail

BRAIN_PARENT="${BRAIN_PARENT:-$HOME/Documents/Claude/Projects/Brain}"
BRAIN_DIR="$BRAIN_PARENT/goldfront-os"
UI_DIR="$BRAIN_PARENT/conrad-command-center"

echo "==> Ensuring repos…"
mkdir -p "$BRAIN_PARENT"
[ -d "$BRAIN_DIR/.git" ] && (cd "$BRAIN_DIR" && git pull) || echo "!! clone goldfront-os into $BRAIN_DIR"
[ -d "$UI_DIR/.git" ] && (cd "$UI_DIR" && git pull) || echo "!! clone conrad-command-center into $UI_DIR"

[ -d "$BRAIN_DIR" ] && [ -d "$UI_DIR" ] || { echo "Repos missing under $BRAIN_PARENT"; exit 1; }

echo "==> Reusing /var/www/dashboard/.env connector keys…"
bash "$BRAIN_DIR/deploy/reuse_manus_env.sh"

echo "==> Full production deploy (build + systemd + nginx)…"
bash "$BRAIN_DIR/deploy/manus_production.sh"

if command -v certbot >/dev/null; then
  echo "==> TLS for brain.theconradteam.com (if DNS A record exists)…"
  sudo certbot --nginx -d brain.theconradteam.com --non-interactive --agree-tos --redirect 2>/dev/null || true
fi

echo ""
echo "==> VERIFY"
curl -sf "http://127.0.0.1:8000/health" && echo
curl -sf "http://127.0.0.1:8000/connectors/status" | python3 -m json.tool 2>/dev/null || curl -sf "http://127.0.0.1:8000/connectors/status"
echo ""
echo "LAN: http://$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}'):8000"
echo "Public (after DNS+cert): https://brain.theconradteam.com"
