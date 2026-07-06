#!/usr/bin/env bash
# Run ON the Manus box (Ubuntu, nginx) after repos exist under ~/Documents/Claude/Projects/Brain/
set -euo pipefail

BRAIN_DIR="${BRAIN_DIR:-$HOME/Documents/Claude/Projects/Brain/goldfront-os}"
UI_DIR="${UI_DIR:-$HOME/Documents/Claude/Projects/Brain/conrad-command-center}"
DOMAIN="${DOMAIN:-brain.theconradteam.com}"

echo "==> Brain: $BRAIN_DIR"
echo "==> UI:    $UI_DIR"

command -v python3 >/dev/null || { echo "Install python3"; exit 1; }
command -v node >/dev/null || { echo "Install Node.js (LTS)"; exit 1; }
command -v npm >/dev/null || { echo "Install npm"; exit 1; }

echo "==> Reusing connector config from existing Manus deployments…"
bash "$BRAIN_DIR/deploy/reuse_manus_env.sh"
if [ ! -f "$UI_DIR/.env" ]; then
  cp "$UI_DIR/.env.example" "$UI_DIR/.env"
fi

echo "==> Building UI..."
( cd "$UI_DIR" && npm install && npm run build )

echo "==> Python venv + deps..."
cd "$BRAIN_DIR"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

echo "==> Installing systemd unit..."
sudo tee /etc/systemd/system/superman-brain.service >/dev/null <<UNIT
[Unit]
Description=Superman Brain (Goldfront OS)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BRAIN_DIR
Environment=GOLDFRONT_OWNER=lindsey
EnvironmentFile=-$BRAIN_DIR/.env
ExecStart=$BRAIN_DIR/.venv/bin/uvicorn brain.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now superman-brain
sudo systemctl status superman-brain --no-pager || true

if command -v nginx >/dev/null; then
  echo "==> nginx site for $DOMAIN"
  NGINX_AVAIL="/etc/nginx/sites-available/$DOMAIN"
  if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    sudo cp "$BRAIN_DIR/deploy/nginx-brain.theconradteam.com.conf" "$NGINX_AVAIL"
  else
    echo "    (no TLS cert yet — HTTP bootstrap; run certbot after DNS)"
    sudo cp "$BRAIN_DIR/deploy/nginx-brain.initial.conf" "$NGINX_AVAIL"
  fi
  sudo ln -sf "$NGINX_AVAIL" "/etc/nginx/sites-enabled/$DOMAIN"
  sudo nginx -t && sudo systemctl reload nginx
fi

echo "==> Local smoke tests:"
curl -sf "http://127.0.0.1:8000/health" && echo " health OK"
STATUS_JSON="$(curl -sf "http://127.0.0.1:8000/connectors/status" || true)"
if [ -n "$STATUS_JSON" ]; then
  echo "$STATUS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'connected_count={d.get(\"connected_count\",0)}')" 2>/dev/null || echo "$STATUS_JSON" | head -c 300
fi
