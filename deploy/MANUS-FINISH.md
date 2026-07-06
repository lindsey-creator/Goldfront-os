# Manus finish — Conrad Command Center + Superman Brain

**Last audited:** 2026-07-06 (Mac local)  
**Manus IP:** `34.26.142.220`  
**Public domain (target):** `https://brain.theconradteam.com`  
**Legacy dashboard (unchanged):** `https://command.theconradteam.com`

---

## Current status checklist

| Item | Status | Notes |
|------|--------|--------|
| `goldfront-os` on GitHub | ✅ | `master` @ `3c1b3c35d9e19e5fd6da071cae7df9136bc74b88` |
| `conrad-command-center` on GitHub | ✅ | `main` @ `fda379d4f2098f9ebff267b34d2512255ebdadb9` |
| Mac git push | ✅ | Both repos **Everything up-to-date** with origin |
| `deploy/manus_bootstrap.sh` on raw GitHub | ✅ | HTTP 200 |
| `deploy/build_and_run.sh` syntax | ✅ | `bash -n` OK |
| Local pytest (83 tests) | ✅ | `.venv` in `goldfront-os` |
| Local uvicorn `:8000` | ✅ | `/health` + `/` return 200 |
| Local `npm run build` | ⚠️ | Not verified in CI shell (no `npm` on PATH); `conrad-command-center/dist/` exists from prior build — run `npm run build` on Mac or Manus |
| `brain-deploy.zip` on Mac | ✅ | See Option C (created at `~/Documents/Claude/Projects/Brain/brain-deploy.zip`) |
| `brain.theconradteam.com/health` | ❓ | **Not responding** from outside — run Option A on Manus to finish |
| Manus repos / systemd | ❓ | **Verify on box** (commands below) |

---

## What you are shipping

- **Backend:** FastAPI “Superman Brain” — `/health`, `/evaluate-deal`, training loop, shadow validation, cockpit reads, `/chat` (Claude if `ANTHROPIC_API_KEY`), ClickUp sync, connector status.
- **Frontend:** Vite/React Command Center — built to `conrad-command-center/dist/`, served by FastAPI on port **8000**.
- **Production script:** `FINISH_ON_MANUS.sh` — pulls env from `/var/www/dashboard/.env`, `npm install && npm run build`, Python venv, **systemd** `superman-brain`, **nginx** for `brain.theconradteam.com`, optional **certbot**.

---

## Option A — GitHub clone (simplest on Manus)

**Requires:** `git`, `python3`, `node`, `npm`, `curl` on the Manus box. Repos must be **public** or use a token (these are public).

In the **Manus terminal**:

```bash
curl -fsSL https://raw.githubusercontent.com/lindsey-creator/Goldfront-os/master/deploy/manus_bootstrap.sh | bash
```

What it does:

1. `mkdir -p ~/Documents/Claude/Projects/Brain`
2. Clone or `git pull` **Goldfront-os** → `goldfront-os/`
3. Clone or `git pull` **conrad-command-center** → `conrad-command-center/`
4. Exec `deploy/FINISH_ON_MANUS.sh`

Manual equivalent:

```bash
export BRAIN_PARENT="$HOME/Documents/Claude/Projects/Brain"
mkdir -p "$BRAIN_PARENT" && cd "$BRAIN_PARENT"

git clone https://github.com/lindsey-creator/Goldfront-os.git goldfront-os \
  || (cd goldfront-os && git pull --ff-only)

git clone https://github.com/lindsey-creator/conrad-command-center.git conrad-command-center \
  || (cd conrad-command-center && git pull --ff-only)

bash "$BRAIN_PARENT/goldfront-os/deploy/FINISH_ON_MANUS.sh"
```

**GitHub URLs:**

- https://github.com/lindsey-creator/Goldfront-os.git
- https://github.com/lindsey-creator/conrad-command-center.git

---

## Option B — scp/rsync from Mac

**Requires:** SSH key on Manus (`lindseyconrad@34.26.142.220`).

On **Mac**:

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/FINISH_FROM_MAC.sh
```

Or rsync only (then SSH and run finish):

```bash
MANUS=lindseyconrad@34.26.142.220
BASE=Documents/Claude/Projects/Brain
EX=(--exclude .git --exclude node_modules --exclude .venv --exclude .env --exclude .memory --exclude __pycache__)

rsync -avz "${EX[@]}" ~/Documents/Claude/Projects/Brain/goldfront-os/ "$MANUS:~/$BASE/goldfront-os/"
rsync -avz "${EX[@]}" ~/Documents/Claude/Projects/Brain/conrad-command-center/ "$MANUS:~/$BASE/conrad-command-center/"

ssh "$MANUS" "bash ~/$BASE/goldfront-os/deploy/FINISH_ON_MANUS.sh"
```

---

## Option C — upload `brain-deploy.zip`

**On Mac** (zip already at):

```
~/Documents/Claude/Projects/Brain/brain-deploy.zip
```

Upload to Manus (pick one):

```bash
scp ~/Documents/Claude/Projects/Brain/brain-deploy.zip lindseyconrad@34.26.142.220:~/
```

**On Manus:**

```bash
cd ~/Documents/Claude/Projects/Brain
unzip -o ~/brain-deploy.zip
bash ~/Documents/Claude/Projects/Brain/goldfront-os/deploy/FINISH_ON_MANUS.sh
```

Recreate zip on Mac anytime:

```bash
cd ~/Documents/Claude/Projects/Brain
rm -f brain-deploy.zip
zip -r brain-deploy.zip goldfront-os conrad-command-center \
  -x '*/node_modules/*' '*/.venv/*' '*/.env' '*/.memory/*' '*/__pycache__/*' '*/.pytest_cache/*' '*/.git/*'
```

---

## Exact verify commands (Manus terminal)

After deploy:

```bash
# Service
sudo systemctl status superman-brain --no-pager
journalctl -u superman-brain -n 30 --no-pager

# App
curl -sf http://127.0.0.1:8000/health
curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool | head -50
curl -sf -o /dev/null -w 'GET / HTTP %{http_code}\n' http://127.0.0.1:8000/

# nginx / public (after DNS)
curl -sf -o /dev/null -w 'https health %{http_code}\n' https://brain.theconradteam.com/health || true
curl -sf https://brain.theconradteam.com/health || echo "DNS/TLS not ready yet"
```

**DNS:** A record `brain.theconradteam.com` → `34.26.142.220` (same as `command.theconradteam.com`).

---

## Quick dev run (no systemd)

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/build_and_run.sh
```

---

## If something fails

| Symptom | Check |
|---------|--------|
| `Missing goldfront-os` | Run Option A or unzip Option C |
| `npm: command not found` | Install Node LTS on Manus |
| `/health` FAIL | `journalctl -u superman-brain -n 50` |
| Connectors empty | `cat goldfront-os/.env`; run `bash deploy/reuse_manus_env.sh` |
| 502 on domain | `sudo nginx -t`; confirm uvicorn on `:8000` |

---

## Finish in 3 steps (simplest path)

1. **Manus terminal:** `curl -fsSL https://raw.githubusercontent.com/lindsey-creator/Goldfront-os/master/deploy/manus_bootstrap.sh | bash`
2. **DNS panel:** A record `brain` → `34.26.142.220` (if not already).
3. **Verify:** `curl -sf http://127.0.0.1:8000/health` on Manus, then `https://brain.theconradteam.com/health` from anywhere.

Old dashboard stays at `https://command.theconradteam.com`.
