#!/usr/bin/env bash
# Run on your Mac. Scans local .env (never prints values) and prints a Manus paste block.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BRAIN_DIR="$(cd "$HERE/.." && pwd)"
ENV_FILE="${BRAIN_DIR}/.env"

VARS=(
  CLICKUP_API_TOKEN CLICKUP_WORKSPACE_ID GHL_API_KEY GHL_LOCATION_ID FIELDY_API_TOKEN
  FIELDY_API_BASE FIELDY_SPEAKER_ME ANTHROPIC_API_KEY
  GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REFRESH_TOKEN
  WHOOP_ACCESS_TOKEN APPLE_HEALTH_EXPORT_PATH
)

is_set() {
  local key="$1" val
  val="$(grep -m1 "^${key}=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
  [ -n "$val" ]
}

echo "==> Local .env ($(dirname "$ENV_FILE"))"
for key in "${VARS[@]}"; do
  is_set "$key" && echo "    ✓ $key" || true
done
echo ""

cat <<'EOF'
================================================================================
PASTE ON MANUS (connectors + Brain restart)
================================================================================
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/reuse_manus_env.sh
grep -q '^FIELDY_API_TOKEN=.' .env || (echo 'Paste FIELDY_API_TOKEN from Mac .env into Manus .env' && nano .env)
sudo systemctl restart superman-brain && sleep 2
curl -sf http://127.0.0.1:8000/health && echo
curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool

# If https://conradstrong.com/health returns HTML (not JSON), fix nginx:
#   deploy/CONRADSTRONG-DEPLOY.md  → paste block on Manus
================================================================================
Add later (not blocking): Google OAuth, Whoop, Apple Health, Anthropic
EOF
