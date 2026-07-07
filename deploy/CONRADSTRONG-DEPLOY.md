# Deploy Conrad Command Center at conradstrong.com

**Manus box:** `102.210.17.121`  
**App:** uvicorn `superman-brain` on `:8000` (serves React `dist` + Brain API)  
**Nginx config:** `deploy/nginx-conradstrong.com.conf`  
**Legacy aliases (same nginx `server_name`):** `commandcenter.theconradteam.com`, `command.theconradteam.com`

---

## Manus network restriction (read first)

Manus runs Brain on the box, but **inbound ports 80 and 443 are not exposed to the public internet**. A GoDaddy A record to `102.210.17.121` will **not** make `https://conradstrong.com` work — HTTPS times out from outside.

**Permanent fix:** [Cloudflare Tunnel](CLOUDFLARE-CONRADSTRONG.md) — run `sudo bash deploy/cloudflared-manus.sh` on Manus after adding the domain to Cloudflare.

**Interim:** Quick tunnel (`cloudflared tunnel --url http://127.0.0.1:8000`) gives a random `*.trycloudflare.com` URL while you set up the real tunnel.

| Check (2026-07-07) | Result |
|--------------------|--------|
| `https://decided-watts-xhtml-disabilities.trycloudflare.com/health` | 200 OK |
| `https://conradstrong.com/health` | Timeout (expected until Cloudflare Tunnel) |

---

## 1. DNS — use Cloudflare Tunnel (not A → Manus IP)

Do **not** point `@` at `102.210.17.121` for public access. Follow **`deploy/CLOUDFLARE-CONRADSTRONG.md`**:

1. Add `conradstrong.com` to Cloudflare; move GoDaddy nameservers to Cloudflare.
2. On Manus: `sudo bash deploy/cloudflared-manus.sh` (tunnel → `localhost:8000`).
3. DNS: CNAME `@` and `www` → tunnel (`*.cfargotunnel.com`), proxied (orange cloud).
4. SSL/TLS mode: **Full**.

Legacy nginx + certbot on Manus (sections below) only matter if you later get direct 80/443 access or use tunnel without terminating TLS locally.

Verify from your Mac after tunnel is live:

```bash
dig +short conradstrong.com
# expect Cloudflare IPs (e.g. 104.x), not 102.210.17.121
curl -sf https://conradstrong.com/health | python3 -m json.tool
```

---

## 2. Paste on Manus terminal (≤25 lines)

Run **after** DNS propagates:

```bash
set -euo pipefail
BRAIN=~/Documents/Claude/Projects/Brain/goldfront-os UI=~/Documents/Claude/Projects/Brain/conrad-command-center
DOMAIN=conradstrong.com SITE=/etc/nginx/sites-available/$DOMAIN
(cd "$BRAIN" && git pull --ff-only) && (cd "$UI" && git pull --ff-only)
(cd "$UI" && npm install && npm run build) && sudo systemctl restart superman-brain && sleep 2
curl -sf http://127.0.0.1:8000/health | python3 -m json.tool
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  sudo cp "$BRAIN/deploy/nginx-conradstrong.com.conf" "$SITE"
else
  sudo tee "$SITE" >/dev/null <<'NGX'
server { listen 80; server_name conradstrong.com www.conradstrong.com commandcenter.theconradteam.com command.theconradteam.com;
  location / { proxy_pass http://127.0.0.1:8000; proxy_http_version 1.1;
    proxy_set_header Host $host; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme; proxy_read_timeout 300s; } }
NGX
fi
sudo ln -sf "$SITE" /etc/nginx/sites-enabled/$DOMAIN && sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d conradstrong.com -d www.conradstrong.com -d commandcenter.theconradteam.com -d command.theconradteam.com --non-interactive --agree-tos --redirect -m lindsey@theconradteam.com
sudo cp "$BRAIN/deploy/nginx-conradstrong.com.conf" "$SITE" && sudo nginx -t && sudo systemctl reload nginx
curl -sf https://conradstrong.com/health | python3 -m json.tool && echo "OK — conradstrong.com live"
```

**Expected:** both curls print JSON (`{"status":"ok","service":"goldfront-brain"}`). `/` serves the latest Command Center UI.

---

## 3. Verify

```bash
curl -sf https://conradstrong.com/health | python3 -m json.tool
curl -sf -o /dev/null -w '%{http_code}\n' https://conradstrong.com/
curl -sf https://commandcenter.theconradteam.com/health | python3 -m json.tool
sudo systemctl status superman-brain --no-pager
```

---

## Notes

- **Public access:** Manus blocks inbound 80/443 — use **Cloudflare Tunnel** (`deploy/CLOUDFLARE-CONRADSTRONG.md`, `deploy/cloudflared-manus.sh`), not an A record to the Manus IP.
- **Primary site:** `https://conradstrong.com` — UI and API share one origin; no `VITE_BRAIN_API` needed in production.
- **Legacy aliases:** `commandcenter.theconradteam.com` and `command.theconradteam.com` stay in the same nginx `server_name` block (see `deploy/nginx-conradstrong.com.conf`). Disable or remove old per-domain nginx site files on Manus if they conflict.
- **Older docs:** `deploy/COMMANDCENTER-DEPLOY.md` documents the `commandcenter` subdomain path; prefer this file for new deploys.
- **systemd:** `superman-brain` — `journalctl -u superman-brain -n 40` if `/health` fails locally.
