# Deploy to Manus (always-on box)

Conrad Command Center (React) + Goldfront OS Brain (FastAPI) on **one port**: `http://<manus>:8000`.

## SSH search result (this Mac)

- `~/.ssh/config` has **no** `Host manus` entry (only `github.com`).
- `command.theconradteam.com` → `34.26.142.220` (likely your public dashboard host).
- SSH to that IP from this machine: **Permission denied (publickey)** — add a `Host manus` block and key before using `deploy-from-dev-mac.sh`.

## Manual setup on the Manus machine (run these ON Manus)

### 1. Prerequisites

- **macOS** (launchd) or **Linux** (systemd)
- Python 3.9+, Node 18+, git

### 2. Clone or copy both repos (sibling folders)

```bash
mkdir -p ~/Documents/Claude/Projects/Brain
cd ~/Documents/Claude/Projects/Brain
# git clone … goldfront-os
# git clone … conrad-command-center
```

### 3. Secrets (optional — never commit)

```bash
cp goldfront-os/.env.example goldfront-os/.env
# Edit goldfront-os/.env on Manus only. Do not rsync .env from your laptop.
```

### 4. One-command install + always-on service

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/manus/install-on-manus.sh
```

This builds the UI, creates `.venv`, installs deps, and registers:

- **macOS**: `~/Library/LaunchAgents/com.goldfront.command-center.plist`
- **Linux**: `superman-brain.service`

### 5. Verify

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
# expect 200
open http://127.0.0.1:8000   # macOS
```

From another device on the same network: `http://<manus-lan-ip>:8000`.

### 6. Logs / restart (macOS)

```bash
tail -f ~/Library/Logs/goldfront/command-center.err.log
launchctl kickstart -k "gui/$(id -u)/com.goldfront.command-center"
```

### 7. Logs / restart (Linux)

```bash
journalctl -u superman-brain -f
sudo systemctl restart superman-brain
```

## Deploy from your Mac (after SSH works)

Add to `~/.ssh/config` on your Mac:

```
Host manus
  HostName <manus-lan-ip-or-tailscale>
  User lindseyconrad
  IdentityFile ~/.ssh/id_ed25519
```

Then:

```bash
export MANUS_SSH=manus
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/manus/deploy-from-dev-mac.sh
```

## Docker (optional)

Build UI first on Manus or your Mac (`npm run build` in `conrad-command-center`). From `Brain/` parent:

```bash
cd goldfront-os/deploy/manus
docker compose build
docker compose up -d
```

## Domain

Your live dashboard is **command.theconradteam.com**. To put this stack on a subdomain, point DNS at Manus and reverse-proxy port 8000 (nginx/Caddy) with HTTPS — same pattern as the existing Command Center.
