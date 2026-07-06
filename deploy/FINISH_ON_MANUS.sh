#!/usr/bin/env bash
# =============================================================================
# FINISH Conrad Command Center + Brain on Manus (Ubuntu)
# Run this IN THE MANUS TERMINAL on the command.theconradteam.com box.
#
#   cd ~/Documents/Claude/Projects/Brain/goldfront-os
#   bash deploy/FINISH_ON_MANUS.sh
#
# Pulls ClickUp/GHL/etc. from /var/www/dashboard/.env → goldfront-os/.env
# Builds UI, starts uvicorn :8000, systemd, nginx, optional certbot.
# =============================================================================
set -euo pipefail

DOMAIN="${DOMAIN:-brain.theconradteam.com}"
BRAIN_PARENT="${BRAIN_PARENT:-$HOME/Documents/Claude/Projects/Brain}"
BRAIN_DIR="${BRAIN_DIR:-$BRAIN_PARENT/goldfront-os}"
UI_DIR="${UI_DIR:-$BRAIN_PARENT/conrad-command-center}"
DASHBOARD_ENV="/var/www/dashboard/.env"

die() { echo "ERROR: $*" >&2; exit 1; }

echo "=============================================="
echo " Conrad Command Center + Brain — Manus deploy"
echo "=============================================="

# --- 0) Repos must exist (sync from Mac if missing) ---
if [ ! -d "$BRAIN_DIR" ] || [ ! -f "$BRAIN_DIR/requirements.txt" ]; then
  cat >&2 <<EOF

  Repos not found at:
    $BRAIN_DIR
    $UI_DIR

  From your Mac (after adding SSH key to this box), run:
    cd ~/Documents/Claude/Projects/Brain/goldfront-os
    bash deploy/FINISH_FROM_MAC.sh

  Or copy both folders to $BRAIN_PARENT on this machine.

EOF
  die "Missing goldfront-os repo"
fi
[ -d "$UI_DIR" ] || die "Missing conrad-command-center at $UI_DIR"

# --- 1) System deps ---
for cmd in python3 node npm curl; do
  command -v "$cmd" >/dev/null || die "Install $cmd first"
done

# --- 2) Wire connector .env from existing command center ---
echo ""
echo "==> [1/6] Connector credentials"
if [ -f "$BRAIN_DIR/deploy/reuse_manus_env.sh" ]; then
  bash "$BRAIN_DIR/deploy/reuse_manus_env.sh"
else
  echo "    reuse_manus_env.sh missing — manual merge from $DASHBOARD_ENV"
  [ -f "$BRAIN_DIR/.env" ] || cp "$BRAIN_DIR/.env.example" "$BRAIN_DIR/.env"
  if [ -f "$DASHBOARD_ENV" ]; then
  BRAIN_DIR="$BRAIN_DIR" python3 <<'PY'
import os
brain = os.environ["BRAIN_DIR"] + "/.env"
dash = "/var/www/dashboard/.env"
def load(p):
    d={}
    if not os.path.isfile(p): return d
    for line in open(p):
        line=line.strip()
        if not line or line.startswith("#") or "=" not in line: continue
        k,v=line.split("=",1); d[k]=v
    return d
b=load(brain); d=load(dash)
alias={"GHL_TEAM_PIT_TOKEN":"GHL_API_KEY","GHL_PERSONAL_PIT_TOKEN":"GHL_API_KEY"}
for src,tgt in alias.items():
    if src in d and tgt not in b: b[tgt]=d[src]
for k in ("CLICKUP_API_TOKEN","GOOGLE_REFRESH_TOKEN","ANTHROPIC_API_KEY","FIELDY_API_TOKEN"):
    if k in d and k not in b: b[k]=d[k]
b.setdefault("GOLDFRONT_OWNER","lindsey")
b.setdefault("CLICKUP_AUTO_SYNC","true")
b.setdefault("CLICKUP_WORKSPACE_ID","90141259054")
if "GHL_API_KEY" in b and "GHL_LOCATION_ID" not in b:
    b["GHL_LOCATION_ID"]="FFdZCVGXSQQThtHZEOYx"
with open(brain,"w") as f:
    for k,v in b.items(): f.write(f"{k}={v}\n")
print("    merged from /var/www/dashboard/.env")
PY
  fi
fi

# UI .env for Vite (same-origin in prod)
if [ ! -f "$UI_DIR/.env" ]; then
  echo "VITE_BRAIN_API=" > "$UI_DIR/.env"
fi

# --- 3) Build React UI ---
echo ""
echo "==> [2/6] npm run build (Command Center UI)"
( cd "$UI_DIR" && npm install && npm run build )

# --- 4) Python venv + uvicorn deps ---
echo ""
echo "==> [3/6] Python venv + requirements"
cd "$BRAIN_DIR"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -U pip
pip install -q -r requirements.txt

# --- 5) systemd (always-on) ---
echo ""
echo "==> [4/6] systemd superman-brain.service"
sudo tee /etc/systemd/system/superman-brain.service >/dev/null <<UNIT
[Unit]
Description=Superman Brain (Goldfront OS + Command Center)
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
sudo systemctl enable superman-brain
sudo systemctl restart superman-brain
sleep 2
sudo systemctl status superman-brain --no-pager || true

# --- 6) nginx reverse proxy ---
echo ""
echo "==> [5/6] nginx → :8000 for $DOMAIN"
if command -v nginx >/dev/null; then
  NGINX_AVAIL="/etc/nginx/sites-available/$DOMAIN"
  if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    sudo cp "$BRAIN_DIR/deploy/nginx-brain.theconradteam.com.conf" "$NGINX_AVAIL"
  else
    sudo cp "$BRAIN_DIR/deploy/nginx-brain.initial.conf" "$NGINX_AVAIL"
  fi
  sudo ln -sf "$NGINX_AVAIL" "/etc/nginx/sites-enabled/$DOMAIN"
  sudo nginx -t
  sudo systemctl reload nginx
else
  echo "    nginx not installed — app on http://$(hostname -I | awk '{print $1}'):8000"
fi

# --- 7) DNS + TLS ---
echo ""
echo "==> [6/6] DNS + HTTPS"
PUBLIC_IP="$(curl -sf ifconfig.me 2>/dev/null || curl -sf icanhazip.com 2>/dev/null || true)"
echo "    Ensure DNS A record: $DOMAIN → ${PUBLIC_IP:-34.26.142.220}"
if command -v certbot >/dev/null && [ -f "/etc/nginx/sites-enabled/$DOMAIN" ]; then
  if ! host "$DOMAIN" 2>/dev/null | grep -q "${PUBLIC_IP:-34.26.142.220}"; then
    echo "    (skip certbot until DNS propagates)"
  else
    sudo certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --redirect \
      -m "${CERTBOT_EMAIL:-lindsey@theconradteam.com}" 2>/dev/null || \
      echo "    certbot failed — run manually: sudo certbot --nginx -d $DOMAIN"
  fi
fi

# --- VERIFY ---
echo ""
echo "=============================================="
echo " VERIFY"
echo "=============================================="
HEALTH="$(curl -sf "http://127.0.0.1:8000/health" 2>/dev/null || true)"
if [ -n "$HEALTH" ]; then
  echo "  /health          OK  $HEALTH"
else
  echo "  /health          FAIL — check: journalctl -u superman-brain -n 40"
  exit 1
fi

STATUS="$(curl -sf "http://127.0.0.1:8000/connectors/status" 2>/dev/null || true)"
if [ -n "$STATUS" ]; then
  CONNECTED="$(echo "$STATUS" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('connected_count',0))" 2>/dev/null || echo "?")"
  echo "  connected_count  $CONNECTED"
  echo "$STATUS" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for name,c in sorted(d.get('connectors',{}).items()):
    s='CONNECTED' if c.get('connected') else 'connect_source'
    print(f'    {name}: {s}')
" 2>/dev/null || echo "  $STATUS" | head -c 400
fi

echo ""
echo "  LIVE (local):   http://127.0.0.1:8000/"
echo "  LIVE (public):  http://${PUBLIC_IP:-YOUR_IP}:8000/"
echo "  LIVE (domain):  https://$DOMAIN/  (after DNS + certbot)"
echo ""
echo "  Old dashboard (unchanged): https://command.theconradteam.com"
echo "=============================================="
