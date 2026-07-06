# Deploy the Superman Brain to the Manus box

One app, one port. The Brain (FastAPI) serves the Command Center UI after a build.
Put it next to your existing `command.theconradteam.com`.

## Prereqs on the Manus box
- Python 3.9+ and Node.js installed
- Both repos side by side:
  ```
  .../Brain/goldfront-os/
  .../Brain/conrad-command-center/
  ```

## 1. One command to build + run
```bash
cd goldfront-os
bash deploy/build_and_run.sh
```
This builds the UI, installs deps, and serves everything at `http://0.0.0.0:8000`.
Open it on the box at `http://localhost:8000`, or from your phone at
`http://<manus-box-ip>:8000`.

## 2. Secrets (optional, add at your pace)
Copy `conrad-command-center/.env.example` and the Brain's env, and fill only the
connectors you want live. Everything works with none set — empty cards show
"connect this," never fake data. Add `ANTHROPIC_API_KEY` to make /chat talk in
your voice.

## 3. Keep it running (so it survives logout/reboot)
Simplest — a systemd service:
```ini
# /etc/systemd/system/superman-brain.service
[Unit]
Description=Superman Brain (Goldfront OS)
After=network.target

[Service]
WorkingDirectory=/home/<you>/Brain/goldfront-os
Environment=GOLDFRONT_OWNER=lindsey
ExecStart=/home/<you>/Brain/goldfront-os/.venv/bin/uvicorn brain.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now superman-brain
```

## 4. Put it on a domain (like the current dashboard)
Point a subdomain (e.g. `brain.theconradteam.com`) at the box and reverse-proxy
:8000 with the same web server that serves your current Command Center (nginx/
Caddy). Add HTTPS. Then it's reachable anywhere — phone, Cybertruck, Starlink.

## Rebuild after changes
Re-run `bash deploy/build_and_run.sh` (or just `npm run build` in the UI, then
restart the service).

## One-shot on the Manus box
After `git pull` (or rsync) both repos:
```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/manus_production.sh
```

Artifacts in this folder:
- `manus_production.sh` — build, systemd, nginx
- `nginx-brain.theconradteam.com.conf` — reverse proxy :8000 (same host as command)
- `superman-brain.service` — reference unit (production script writes `/etc/systemd/system/...`)

## DNS
Add an **A record** `brain.theconradteam.com` → same IP as `command.theconradteam.com` (currently `34.26.142.220`).

## SSH from Lindsey's Mac
If `Permission denied (publickey)`, add this Mac's key on the Manus box:
```bash
# on Mac:
cat ~/.ssh/id_ed25519.pub
# on Manus (~/.ssh/authorized_keys):
# paste the line, then from Mac:
ssh lindseyconrad@34.26.142.220
```
