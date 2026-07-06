# Deploy the Superman Brain to the Manus box

One app, one port. FastAPI serves the Command Center UI after `npm run build`.

**Manus box:** `102.210.17.121` (same host as `command.theconradteam.com`)  
**Target domain:** `brain.theconradteam.com` → A record to that IP  
**Layout on the server:**

```
~/Documents/Claude/Projects/Brain/goldfront-os/
~/Documents/Claude/Projects/Brain/conrad-command-center/
```

Full finish checklist and three sync options: **`deploy/MANUS-FINISH.md`**.

---

## Fastest finish (on Manus terminal)

**Option A — GitHub clone + full production setup (recommended):**

```bash
curl -fsSL https://raw.githubusercontent.com/lindsey-creator/Goldfront-os/master/deploy/manus_bootstrap.sh | bash
```

That clones/pulls both repos, then runs `deploy/FINISH_ON_MANUS.sh` (env merge from `/var/www/dashboard/.env`, UI build, systemd, nginx, optional certbot).

**Option B — repos already on the box:**

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
git pull --ff-only
cd ../conrad-command-center && git pull --ff-only
bash ~/Documents/Claude/Projects/Brain/goldfront-os/deploy/FINISH_ON_MANUS.sh
```

**From Lindsey's Mac (rsync + remote finish):**

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/FINISH_FROM_MAC.sh
```

---

## Dev / smoke: build + run (no systemd)

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/build_and_run.sh
```

Serves at `http://0.0.0.0:8000`. Requires Python 3.9+, Node.js, and npm on the box.

---

## Verify (on Manus)

```bash
curl -sf http://127.0.0.1:8000/health
curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool | head -40
curl -sf -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/
```

After DNS + TLS:

```bash
curl -sf https://brain.theconradteam.com/health
```

---

## Secrets (optional)

`FINISH_ON_MANUS.sh` runs `deploy/reuse_manus_env.sh` to copy connector keys from `/var/www/dashboard/.env` into `goldfront-os/.env`. Add `ANTHROPIC_API_KEY` for live `/chat`. Empty connectors show “connect this” in the UI — no fake data.

---

## systemd (reference)

Production install is handled by `FINISH_ON_MANUS.sh` / `manus_production.sh`. Reference unit: `deploy/superman-brain.service`.

```bash
sudo systemctl status superman-brain
journalctl -u superman-brain -n 40 --no-pager
```

---

## Artifacts in `deploy/`

| File | Purpose |
|------|---------|
| `MANUS-FINISH.md` | Status checklist + Options A/B/C |
| `manus_bootstrap.sh` | One-curl GitHub clone + finish |
| `FINISH_ON_MANUS.sh` | Full production deploy on Ubuntu |
| `FINISH_FROM_MAC.sh` | rsync from Mac + remote finish |
| `build_and_run.sh` | Local build + uvicorn only |
| `manus_production.sh` | Build + systemd + nginx (no clone) |
| `reuse_manus_env.sh` | Merge dashboard `.env` → brain |
| `nginx-brain.*.conf` | Reverse proxy :8000 |

---

## Rebuild after code changes

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/FINISH_ON_MANUS.sh
# or quick: bash deploy/build_and_run.sh
```

---

## SSH from Mac

If `Permission denied (publickey)`:

```bash
# Mac:
cat ~/.ssh/id_ed25519.pub
# Manus: paste into ~/.ssh/authorized_keys
ssh lindseyconrad@102.210.17.121
```

## GitHub repos

- https://github.com/lindsey-creator/Goldfront-os.git (`master`)
- https://github.com/lindsey-creator/conrad-command-center.git (`main`)
