# Deploy Conrad Command Center at commandcenter.theconradteam.com

**Manus box:** `102.210.17.121`  
**App:** uvicorn `superman-brain` on `:8000` (serves React `dist` + Brain API)  
**Nginx config:** `deploy/nginx-commandcenter.theconradteam.com.conf`

---

## 1. DNS (GoDaddy)

Add an **A record** in GoDaddy DNS for `theconradteam.com`:

| Type | Name            | Value          | TTL  |
|------|-----------------|----------------|------|
| A    | `commandcenter` | `102.210.17.121` | 600s (or default) |

Full hostname: `commandcenter.theconradteam.com` → Manus IP.

Verify from your Mac:

```bash
dig +short commandcenter.theconradteam.com A
# expect: 102.210.17.121
```

Certbot will fail until DNS resolves to the Manus box.

---

## 2. Paste on Manus terminal (≤30 lines)

Run **after** DNS propagates:

```bash
set -euo pipefail
BRAIN=~/Documents/Claude/Projects/Brain/goldfront-os UI=~/Documents/Claude/Projects/Brain/conrad-command-center
DOMAIN=commandcenter.theconradteam.com SITE=/etc/nginx/sites-available/$DOMAIN
(cd "$BRAIN" && git pull --ff-only) && (cd "$UI" && git pull --ff-only)
(cd "$UI" && npm install && npm run build) && sudo systemctl restart superman-brain && sleep 2
curl -sf http://127.0.0.1:8000/health | python3 -m json.tool
if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
  sudo cp "$BRAIN/deploy/nginx-commandcenter.theconradteam.com.conf" "$SITE"
else
  sudo tee "$SITE" >/dev/null <<'NGX'
server { listen 80; server_name commandcenter.theconradteam.com;
  location / { proxy_pass http://127.0.0.1:8000; proxy_http_version 1.1;
    proxy_set_header Host $host; proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme; proxy_read_timeout 300s; } }
NGX
fi
sudo ln -sf "$SITE" /etc/nginx/sites-enabled/$DOMAIN && sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --redirect -m lindsey@theconradteam.com
sudo cp "$BRAIN/deploy/nginx-commandcenter.theconradteam.com.conf" "$SITE" && sudo nginx -t && sudo systemctl reload nginx
curl -sf "https://$DOMAIN/health" | python3 -m json.tool && echo "OK — commandcenter live"
```

**Expected:** both curls print JSON (`{"status":"ok","service":"goldfront-brain"}`). `/` serves the latest Command Center UI.

---

## 3. Verify

```bash
curl -sf https://commandcenter.theconradteam.com/health | python3 -m json.tool
curl -sf -o /dev/null -w '%{http_code}\n' https://commandcenter.theconradteam.com/
sudo systemctl status superman-brain --no-pager
```

---

## Notes

- **Same origin:** UI and API share `commandcenter.theconradteam.com` — no `VITE_BRAIN_API` needed in production.
- **Legacy:** `command.theconradteam.com` may still serve the old dashboard; see `deploy/FIX-COMMAND-NGINX.md` to point it at Brain instead.
- **systemd:** `superman-brain` — `journalctl -u superman-brain -n 40` if `/health` fails locally.
