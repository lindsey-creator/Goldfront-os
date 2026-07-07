# Fix command.theconradteam.com nginx → Brain (uvicorn :8000)

**Symptom:** `https://command.theconradteam.com` serves stale static HTML (June 15 dashboard) for all paths including `/health`. Brain may be running on `:8000` locally but nginx is not proxying.

**Repo note:** `deploy/` has `nginx-brain.theconradteam.com.conf` and `nginx-brain.initial.conf` only — **no** `nginx-command.theconradteam.com.conf`. The live command site was likely `root /var/www/dashboard` (or similar) on the Manus box. This fix replaces that with the same `proxy_pass` pattern as the brain config.

**Reference:** `deploy/nginx-brain.theconradteam.com.conf`, `deploy/DEPLOY.md`

---

## Paste on Manus terminal (≤25 lines)

```bash
set -euo pipefail
BRAIN=~/Documents/Claude/Projects/Brain/goldfront-os UI=~/Documents/Claude/Projects/Brain/conrad-command-center
echo "==> existing nginx for command:"; sudo grep -l command.theconradteam.com /etc/nginx/sites-enabled/* 2>/dev/null | xargs -r sudo cat
curl -sf http://127.0.0.1:8000/health | python3 -m json.tool || { sudo systemctl start superman-brain; sleep 2; curl -sf http://127.0.0.1:8000/health; }
(cd "$UI" && npm install && npm run build) && sudo systemctl restart superman-brain && sleep 2
sudo tee /etc/nginx/sites-available/command.theconradteam.com >/dev/null <<'NGX'
server { listen 80; server_name command.theconradteam.com; return 301 https://$host$request_uri; }
server {
    listen 443 ssl http2; server_name command.theconradteam.com;
    ssl_certificate /etc/letsencrypt/live/command.theconradteam.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/command.theconradteam.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf; ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
    # location /car { alias /var/www/cybertruck; try_files $uri $uri/ =404; }  # uncomment if cybertruck needs separate static
    location / { proxy_pass http://127.0.0.1:8000; proxy_http_version 1.1;
        proxy_set_header Host $host; proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s; }
}
NGX
sudo ln -sf /etc/nginx/sites-available/command.theconradteam.com /etc/nginx/sites-enabled/command.theconradteam.com
sudo nginx -t && sudo systemctl reload nginx
curl -sf http://127.0.0.1:8000/health | python3 -m json.tool
curl -sf https://command.theconradteam.com/health | python3 -m json.tool && echo "OK — command proxies to Brain"
```

**Expected:** both curls print JSON (e.g. `{"status":"ok",...}`). `/` serves the latest React build from `conrad-command-center/dist` via uvicorn (`brain/main.py` mounts dist after `npm run build`).

**If cert paths differ:** `sudo ls /etc/letsencrypt/live/` and edit the `ssl_certificate` lines before `nginx -t`.
