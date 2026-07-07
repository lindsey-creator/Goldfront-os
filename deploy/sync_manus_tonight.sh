#!/usr/bin/env bash
# One command on Manus to pull latest Brain + Command Center UI (everything except Cloudflare).
# Run on Manus Ubuntu box:
#   bash ~/Documents/Claude/Projects/Brain/goldfront-os/deploy/sync_manus_tonight.sh
set -euo pipefail

BRAIN_PARENT="${BRAIN_PARENT:-$HOME/Documents/Claude/Projects/Brain}"

cd "$BRAIN_PARENT/goldfront-os" && git pull
cd "$BRAIN_PARENT/conrad-command-center" && git pull && npm install && npm run build
sudo systemctl restart superman-brain

echo ""
echo "==> VERIFY"
curl -sf "http://127.0.0.1:8000/health" && echo
curl -sf "http://127.0.0.1:8000/connectors/status" | python3 -m json.tool 2>/dev/null | head -20 || true
echo ""
echo "LIVE: http://127.0.0.1:8000/"
echo "Tunnel (if running on Manus): https://decided-watts-xhtml-disabilities.trycloudflare.com/"
echo "Tomorrow: Cloudflare tunnel → conradstrong.com (see deploy/TOMORROW-CLOUDFLARE.md)"
