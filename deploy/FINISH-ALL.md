# FINISH ALL — 15-minute checklist

**Goal:** 7/7 connectors local · Brain live on Mac · Manus synced · `conradstrong.com` via Cloudflare.

**Mac env file:** `~/Documents/Claude/Projects/Brain/goldfront-os/.env`  
**Live dashboard (Manus):** https://conrad-dash-3dzqldfq.manus.space/  
**Never commit `.env` or paste secrets in chat.**

---

## 0. Where you are right now (2026-07-08)

| Item | Status |
|------|--------|
| Brain on Mac (`:8000`) | ✅ Running |
| Echo command deck UI | ✅ `http://127.0.0.1:8000/` |
| Live data (ClickUp, GHL, Fieldy) | ✅ `/brief/daily`, `/watchlist`, `/crm/ghl` |
| Echo `/chat` (Anthropic) | ✅ `ANTHROPIC_API_KEY` SET — live Claude narration |
| Connectors | **3/7** — ClickUp, Fieldy, GHL |
| Still needed | Google (Calendar + Gmail), Whoop, Apple Health (optional) |

---

## 1. Mac — finish connectors (≈10 min)

### Already SET (do nothing)

- `ANTHROPIC_API_KEY`
- `CLICKUP_API_TOKEN`, `CLICKUP_WORKSPACE_ID`
- `FIELDY_API_TOKEN`
- `GHL_API_KEY`, `GHL_LOCATION_ID`

> **GHL note:** Connected to personal sub-account `3nUeqiIgQEtLuQJUbWVO`. For team CRM, set `GHL_LOCATION_ID=FFdZCVGXSQQThtHZEOYx` and restart Brain.

### A. Google Calendar + Gmail (one OAuth — unlocks 2 connectors)

1. Open **Chrome Profile 10** → [Google Cloud Credentials](https://console.cloud.google.com/apis/credentials)
2. Create **OAuth 2.0 Client ID** → type **Desktop app**
3. Enable **Calendar API** + **Gmail API** on the project
4. Add redirect URI (pick one flow — do not mix):
   - **Recommended:** `http://127.0.0.1:8000/google/oauth/callback` → then open `http://127.0.0.1:8000/connect/google`
   - **CLI script:** `http://localhost:8765/oauth2callback` → run `python3 scripts/google_oauth_setup.py` and **keep terminal open** until sign-in finishes
5. Paste into `.env`:
   - `GOOGLE_CLIENT_ID`
   - `GOOGLE_CLIENT_SECRET`
6. Complete OAuth (Brain flow: visit `/connect/google`; CLI: run script below):

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
# Only if you registered the :8765 redirect URI:
python3 scripts/google_oauth_setup.py
```

7. Restart Brain:

```bash
pkill -f 'uvicorn brain.main:app' 2>/dev/null; sleep 1
cd ~/Documents/Claude/Projects/Brain/goldfront-os
source .venv/bin/activate
nohup uvicorn brain.main:app --host 0.0.0.0 --port 8000 > /tmp/goldfront-brain.log 2>&1 &
```

8. Verify → `connected_count` should be **5/7**:

```bash
curl -s http://127.0.0.1:8000/connectors/status | python3 -m json.tool
curl -s http://127.0.0.1:8000/calendar/week | python3 -m json.tool
```

**Or use the interactive helper** (prompts for missing keys, restarts Brain):

```bash
bash ~/Documents/Claude/Projects/Brain/goldfront-os/deploy/connect_interactive.sh
```

### B. Whoop (persistent OAuth — does not disconnect)

Static `WHOOP_ACCESS_TOKEN` expires in ~1 hour. Use OAuth refresh tokens instead.

**Full guide:** [deploy/WHOOP-SETUP.md](./WHOOP-SETUP.md)

1. Register app at [developer.whoop.com](https://developer.whoop.com)
2. Redirect URI: `http://localhost:8787/oauth2callback`
3. Add `WHOOP_CLIENT_ID` and `WHOOP_CLIENT_SECRET` to `.env`
4. Run one-time browser flow:

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
python3 scripts/whoop_oauth_setup.py
```

5. Restart Brain (same commands as Google step 7)
6. Verify: `curl -s http://127.0.0.1:8000/health/metrics | python3 -m json.tool`

Brain auto-refreshes access tokens and rotates `WHOOP_REFRESH_TOKEN` in `.env`.

### C. Apple Health (optional — skip on Mac unless you have a JSON export)

1. Only if you have a local health JSON export path
2. Set `APPLE_HEALTH_EXPORT_PATH=/absolute/path/to/export.json` in `.env`
3. Restart Brain

---

## 2. Mac — verify UI (≈2 min)

```bash
open http://127.0.0.1:8000/
curl -sf http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' -d '{"message":"status check"}' | python3 -m json.tool | head -20
```

**Pass:** Echo command deck loads · Rhino Core hero · priority horns · intel lanes show live ClickUp/GHL/Fieldy data · Calendar/Health lanes say “connect” until wired.

**Rebuild UI only if you pulled new command-center commits:**

```bash
cd ~/Documents/Claude/Projects/Brain/conrad-command-center
git pull && npm install && npm run build
# Restart Brain after build
```

---

## 3. Manus — one command sync

SSH to Manus (`102.210.17.121`):

```bash
bash ~/Documents/Claude/Projects/Brain/goldfront-os/deploy/sync_manus_tonight.sh
```

Or paste manually:

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os && git pull
cd ~/Documents/Claude/Projects/Brain/conrad-command-center && git pull && npm install && npm run build
bash ~/Documents/Claude/Projects/Brain/goldfront-os/deploy/reuse_manus_env.sh
# Copy Mac .env secrets Manus is still missing (Fieldy + Google/Whoop OAuth):
#   scp ~/Documents/Claude/Projects/Brain/goldfront-os/.env lindseyconrad@102.210.17.121:~/Documents/Claude/Projects/Brain/goldfront-os/.env
sudo systemctl restart superman-brain
sleep 2
curl -sf http://127.0.0.1:8000/health && echo
curl -s http://127.0.0.1:8000/connectors/status | python3 -m json.tool
echo "LIVE: http://127.0.0.1:8000/"
echo "Dashboard: https://conrad-dash-3dzqldfq.manus.space/"
```

**Pass:** `/health` → `ok` · connector count matches Mac · UI loads on Manus.

---

## 4. Env vars checklist (Manus `.env`)

Path: `~/Documents/Claude/Projects/Brain/goldfront-os/.env`

| Variable | Notes |
|----------|-------|
| `ANTHROPIC_API_KEY` | ✅ Set on Mac — copy to Manus |
| `GOLDFRONT_OWNER` | `lindsey` |
| `CLICKUP_API_TOKEN` | ClickUp Settings → Apps |
| `CLICKUP_WORKSPACE_ID` | `90141259054` |
| `CLICKUP_AUTO_SYNC` | `true` |
| `GHL_API_KEY` | GHL Private Integration |
| `GHL_LOCATION_ID` | Team: `FFdZCVGXSQQThtHZEOYx` |
| `FIELDY_API_TOKEN` | **Copy from Mac** — do not regenerate |
| `FIELDY_API_BASE` | `https://api.fieldy.ai` |
| `FIELDY_SPEAKER_ME` | `Lindsey` |
| `GOOGLE_CLIENT_ID` | Google Cloud OAuth |
| `GOOGLE_CLIENT_SECRET` | |
| `GOOGLE_REFRESH_TOKEN` | `scripts/google_oauth_setup.py` |
| `GOOGLE_CALENDAR_ID` | `primary` |
| `WHOOP_CLIENT_ID` | See [WHOOP-SETUP.md](./WHOOP-SETUP.md) |
| `WHOOP_CLIENT_SECRET` | |
| `WHOOP_REFRESH_TOKEN` | `scripts/whoop_oauth_setup.py` |
| `APPLE_HEALTH_EXPORT_PATH` | Optional local JSON |

---

## 5. Cloudflare — `conradstrong.com` (tomorrow or now)

**Prerequisites:** Manus Brain healthy · repos pulled · UI built.

On Manus:

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
sudo bash deploy/cloudflared-manus.sh
```

Then in **Cloudflare dashboard** for `conradstrong.com`:

1. **Remove** A record `@` → `102.210.17.121`
2. **Add** CNAME `@` → `<tunnel-id>.cfargotunnel.com` (Proxied)
3. **Add** CNAME `www` → same target (Proxied)
4. SSL/TLS mode: **Full**

Verify:

```bash
curl -sf https://conradstrong.com/health
curl -sf https://conradstrong.com/connectors/status
open https://conradstrong.com/
```

Full reference: `deploy/TOMORROW-CLOUDFLARE.md`

---

## 6. Finish line — you are DONE when

- [ ] `curl -s http://127.0.0.1:8000/connectors/status` → **`connected_count`: 5 or 7** (5 without Whoop/Apple; 7 with all)
- [ ] `http://127.0.0.1:8000/` → Echo deck with **live** ClickUp + GHL + Fieldy lanes
- [ ] `/chat` returns Claude narration (not fallback stub)
- [ ] Manus `sync_manus_tonight.sh` run · `superman-brain` restarted · same connector count
- [ ] https://conrad-dash-3dzqldfq.manus.space/ loads with live connectors
- [ ] `https://conradstrong.com/health` → `ok` (after Cloudflare step)

**You are NOT blocked on code.** Remaining work is env secrets (Google ×3, Whoop OAuth ×3) + optional Apple Health + Cloudflare DNS.

---

## Quick links (Chrome Profile 10)

| Secret | Where |
|--------|--------|
| `GOOGLE_CLIENT_ID` / `SECRET` | https://console.cloud.google.com/apis/credentials |
| `GOOGLE_REFRESH_TOKEN` | `python3 scripts/google_oauth_setup.py` (after ID/secret in `.env`) |
| `WHOOP_CLIENT_ID` / `SECRET` / `REFRESH_TOKEN` | [WHOOP-SETUP.md](./WHOOP-SETUP.md) → `python3 scripts/whoop_oauth_setup.py` |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys *(already SET)* |

## Related docs

| Doc | Purpose |
|-----|---------|
| [CONNECT-EVERYTHING.md](./CONNECT-EVERYTHING.md) | Detailed connector setup |
| [WHOOP-SETUP.md](./WHOOP-SETUP.md) | Whoop OAuth (persistent) |
| [sync_manus_tonight.sh](./sync_manus_tonight.sh) | One-command Manus sync |
