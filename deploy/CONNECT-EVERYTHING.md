# Connect Everything — Conrad Command Center / Superman Brain on Manus

**Last updated:** 2026-07-06  
**Manus IP:** `102.210.17.121`  
**Brain service:** `superman-brain` (systemd)  
**Env file:** `~/Documents/Claude/Projects/Brain/goldfront-os/.env`  
**Legacy dashboard env (auto-merge source):** `/var/www/dashboard/.env`

Each connector is independent. Add only the keys you need. Restart the Brain after any `.env` change.

---

## Status checklist

| Connector | Env vars | Manus status | Priority |
|-----------|----------|--------------|----------|
| **GoHighLevel** | `GHL_API_KEY`, `GHL_LOCATION_ID` | ✅ Connected (reported) | Done |
| **ClickUp** | `CLICKUP_API_TOKEN`, `CLICKUP_WORKSPACE_ID` | ⏳ Pending | **High** — tasks, memory sync |
| **Anthropic /chat** | `ANTHROPIC_API_KEY` | ⏳ Pending | **High** — live Brain narration |
| **Google Calendar** | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` | ⏳ Pending | Medium |
| **Gmail** | Same Google OAuth trio | ⏳ Pending | Medium (shares Google OAuth) |
| **Fieldy** | `FIELDY_API_TOKEN` | ✓ (local `.env`) | Medium |
| **Whoop** | `WHOOP_ACCESS_TOKEN` | ⏳ Pending | Low |
| **Apple Health** | `APPLE_HEALTH_EXPORT_PATH` | ⏳ Pending | Low (local JSON file only) |

**Recommended order:** ClickUp → Anthropic → Google (Calendar + Gmail together) → Fieldy → Whoop → Apple Health.

---

## Full `.env` template

Copy to `~/Documents/Claude/Projects/Brain/goldfront-os/.env`. Never commit this file.

```bash
# ── Core ─────────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY=                    # https://console.anthropic.com/settings/keys
GOLDFRONT_OWNER=lindsey

# ── ClickUp ──────────────────────────────────────────────────────────────────
CLICKUP_API_TOKEN=                    # https://app.clickup.com/settings/apps → API Token
CLICKUP_WORKSPACE_ID=90141259054      # Team/Workspace ID (Settings → Workspaces)
CLICKUP_AUTO_SYNC=true

# ── GoHighLevel ──────────────────────────────────────────────────────────────
GHL_API_KEY=                          # Sub-account → Settings → Private Integrations → Create
GHL_LOCATION_ID=                      # Location ID from GHL sub-account URL or settings

# ── Fieldy ─────────────────────────────────────────────────────────────────
FIELDY_API_TOKEN=                     # copy from your Mac goldfront-os/.env (you already set this)
FIELDY_API_BASE=https://api.fieldy.ai
FIELDY_SPEAKER_ME=Lindsey

# ── Google (Calendar + Gmail share one OAuth app) ────────────────────────────
GOOGLE_CLIENT_ID=                     # https://console.cloud.google.com/apis/credentials
GOOGLE_CLIENT_SECRET=                 # Same OAuth 2.0 Client ID
GOOGLE_REFRESH_TOKEN=                 # OAuth flow with Calendar + Gmail scopes (see below)
GOOGLE_CALENDAR_ID=primary

# ── Whoop ────────────────────────────────────────────────────────────────────
WHOOP_ACCESS_TOKEN=                   # https://developer.whoop.com → OAuth → access token

# ── Apple Health (display only — no cloud API) ───────────────────────────────
APPLE_HEALTH_EXPORT_PATH=             # Path on Manus to a JSON export your sync writes

# ── Optional / legacy ────────────────────────────────────────────────────────
CLICKUP_MCP_URL=https://mcp.clickup.com/mcp
DECISION_HALFLIFE_DAYS=180
```

### Where to get each token

| Variable | Where to get it |
|----------|-----------------|
| `ANTHROPIC_API_KEY` | [Anthropic Console → API Keys](https://console.anthropic.com/settings/keys) |
| `CLICKUP_API_TOKEN` | [ClickUp Settings → Apps](https://app.clickup.com/settings/apps) → Generate API Token |
| `CLICKUP_WORKSPACE_ID` | ClickUp → Workspace settings, or `90141259054` (default in `.env.example`) |
| `GHL_API_KEY` | GHL sub-account → **Settings → Private Integrations** → Create → copy token |
| `GHL_LOCATION_ID` | GHL location settings or URL (`/location/{id}/`) |
| `FIELDY_API_TOKEN` | **Already on your Mac** — copy `FIELDY_API_TOKEN` from local `goldfront-os/.env` to Manus `.env` (do not hunt a new token) |
| `GOOGLE_CLIENT_ID` / `SECRET` | [Google Cloud Console → Credentials](https://console.cloud.google.com/apis/credentials) → OAuth 2.0 Client |
| `GOOGLE_REFRESH_TOKEN` | One-time OAuth consent with scopes: `calendar.readonly`, `gmail.readonly` (see Google section below) |
| `WHOOP_ACCESS_TOKEN` | [Whoop Developer Portal](https://developer.whoop.com) → register app → OAuth |
| `APPLE_HEALTH_EXPORT_PATH` | Local path on Manus where a health sync script drops JSON |

---

## Fast path on Manus — reuse existing secrets

**Fieldy:** copy `FIELDY_API_TOKEN` from your Mac `goldfront-os/.env` into Manus `goldfront-os/.env`. Do not generate a new token in the Fieldy dashboard unless the Mac value is missing.

Manus may also have connector keys in `/var/www/dashboard/.env` (command center). Pull them into the Brain:

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
bash deploy/reuse_manus_env.sh
sudo systemctl restart superman-brain
curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool
```

`reuse_manus_env.sh` scans `/var/www/dashboard/.env` and other env files on the box. It **never prints secret values**. It also maps legacy aliases:

- `GHL_TEAM_PIT_TOKEN` or `GHL_PERSONAL_PIT_TOKEN` → `GHL_API_KEY`
- `GHL_LOCATION_ID` from dashboard env

**Fieldy:** `reuse_manus_env.sh` does **not** pull `FIELDY_API_TOKEN`. Copy it from your Mac:

```bash
# On Mac — copy full .env (includes FIELDY_API_TOKEN) to Manus
scp ~/Documents/Claude/Projects/Brain/goldfront-os/.env \
  lindseyconrad@102.210.17.121:~/Documents/Claude/Projects/Brain/goldfront-os/.env
```

Or paste `FIELDY_API_TOKEN` from Mac `.env` into Manus `.env` manually.

---

## Manus terminal — edit `.env` manually

```bash
# 1. Open env file
nano ~/Documents/Claude/Projects/Brain/goldfront-os/.env
# or: code ~/Documents/Claude/Projects/Brain/goldfront-os/.env

# 2. Add missing keys (paste values from your password manager / dashboards)

# 3. Restart Brain
sudo systemctl restart superman-brain

# 4. Confirm service is up
sudo systemctl status superman-brain --no-pager
journalctl -u superman-brain -n 20 --no-pager

# 5. Verify connectors (no secrets in output)
curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool

# 6. Optional — test /chat (needs ANTHROPIC_API_KEY)
curl -sf -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"What connectors are live?"}' | python3 -m json.tool | head -30
```

### Check which keys are set (safe — no values printed)

```bash
ENV=~/Documents/Claude/Projects/Brain/goldfront-os/.env
for key in ANTHROPIC_API_KEY CLICKUP_API_TOKEN CLICKUP_WORKSPACE_ID \
  GHL_API_KEY GHL_LOCATION_ID FIELDY_API_TOKEN \
  GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET GOOGLE_REFRESH_TOKEN \
  WHOOP_ACCESS_TOKEN APPLE_HEALTH_EXPORT_PATH; do
  if grep -q "^${key}=.\+" "$ENV" 2>/dev/null; then echo "$key=SET"; else echo "$key=UNSET"; fi
done
```

---

## One-block paste prompt for Manus agent

Paste this into a **new Manus chat** on your cloud computer (Lindsey Conrad's Cloud Computer):

```
Connect all Superman Brain integrations on this box.

Context:
- Brain repo: ~/Documents/Claude/Projects/Brain/goldfront-os
- Command Center UI: ~/Documents/Claude/Projects/Brain/conrad-command-center
- Env file: ~/Documents/Claude/Projects/Brain/goldfront-os/.env
- systemd service: superman-brain (port 8000)
- GHL is already connected. ClickUp, Anthropic, Google, Whoop, Apple Health are still pending.
- Fieldy: copy `FIELDY_API_TOKEN` from Mac `goldfront-os/.env` into Manus `.env` (do not hunt dashboard env).

Do this in order:
1. Run: bash ~/Documents/Claude/Projects/Brain/goldfront-os/deploy/reuse_manus_env.sh
   (pulls keys from /var/www/dashboard/.env — never print secret values)
2. Show which env vars are SET vs UNSET using the safe grep loop in deploy/CONNECT-EVERYTHING.md
3. For any still-UNSET vars, look in /var/www/dashboard/.env, ~/.env, and other env files on this machine. Add them to goldfront-os/.env without echoing values in chat.
4. If CLICKUP_API_TOKEN is missing, help me create one at https://app.clickup.com/settings/apps
5. If ANTHROPIC_API_KEY is missing, check /var/www/dashboard/.env or ask me to paste it privately into .env
6. sudo systemctl restart superman-brain
7. curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool
8. Report: connected_count, which connectors flipped to connected, and what I still need to add manually.

Never commit .env or paste secrets into chat. Only report variable NAMES and SET/UNSET status.
```

---

## Verify each connector

After restart, `GET /connectors/status` returns `{ connected: true/false, env_vars: [...] }` per connector.

```bash
curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool
```

| Connector | `connected: true` when | Extra smoke test |
|-----------|------------------------|------------------|
| `ghl` | `GHL_API_KEY` + `GHL_LOCATION_ID` set | Open Command Center → Connections → GoHighLevel shows **Live** |
| `clickup` | `CLICKUP_API_TOKEN` + `CLICKUP_WORKSPACE_ID` set | Connections → ClickUp **Live**; check Brain logs for sync |
| `google_calendar` | Google OAuth trio set | Connections → Google Calendar **Live** |
| `gmail` | Same Google OAuth trio | Connections → Gmail **Live** |
| `fieldy` | `FIELDY_API_TOKEN` set | Connections → Fieldy **Live** |
| `whoop` | `WHOOP_ACCESS_TOKEN` set | Connections → Whoop **Live** |
| `apple_health` | `APPLE_HEALTH_EXPORT_PATH` points to readable JSON | Connections → Apple Health **Live** |

**Anthropic** is not in `/connectors/status` — test via `/chat`:

```bash
curl -sf -X POST http://127.0.0.1:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"ping"}' | python3 -c "import sys,json; r=json.load(sys.stdin); print('claude' if 'fallback' not in r.get('mode','').lower() else 'fallback')"
```

Or open **Connections** in the UI at `http://127.0.0.1:8000/` (or `https://conradstrong.com` once DNS is live).

---

## Google OAuth (Calendar + Gmail) — one-time setup

Both connectors share `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN`.

1. [Google Cloud Console](https://console.cloud.google.com/) → create project → enable **Google Calendar API** and **Gmail API**.
2. **Credentials** → OAuth 2.0 Client ID (Desktop or Web).
3. Run OAuth consent once with scopes:
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/gmail.readonly`
4. Save the **refresh token** to `GOOGLE_REFRESH_TOKEN` in `.env`.

Tools: [Google OAuth Playground](https://developers.google.com/oauthplayground/) (use your own client ID/secret) or a small local script.

---

## Copy from Mac local `.env` (variable names only)

If your Mac `goldfront-os/.env` has keys Manus is missing, **copy the values manually** (password manager or `scp` the file — never paste secrets in chat):

```bash
# On Mac — copy .env to Manus (excludes from git already)
scp ~/Documents/Claude/Projects/Brain/goldfront-os/.env \
  lindseyconrad@102.210.17.121:~/Documents/Claude/Projects/Brain/goldfront-os/.env

# On Manus after copy
sudo systemctl restart superman-brain
```

**Mac keys known SET (2026-07-06):** `GOLDFRONT_OWNER`, `GHL_API_KEY`, `GHL_LOCATION_ID`, `CLICKUP_WORKSPACE_ID`, `CLICKUP_MCP_URL`, `DECISION_HALFLIFE_DAYS`  
**Mac keys UNSET:** `ANTHROPIC_API_KEY`, `CLICKUP_API_TOKEN` (and most others)

Even on Mac, ClickUp needs `CLICKUP_API_TOKEN` — workspace ID alone is not enough.

---

## UI: Connections page

Built into Command Center (served by Brain on port 8000):

1. Open `http://127.0.0.1:8000/` on Manus (or public URL when DNS works).
2. Navigate to **Connections**.
3. Each card shows required env var names and **Live** / **Not connected** status.

Env var hints match `conrad-command-center/src/components/Connections.tsx`.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| All connectors `connected: false` | Run `reuse_manus_env.sh`; confirm `.env` path; restart service |
| GHL works, ClickUp doesn't | Need `CLICKUP_API_TOKEN` (not just workspace ID) |
| `/chat` uses fallback | Add `ANTHROPIC_API_KEY`; restart |
| Service won't start | `journalctl -u superman-brain -n 50` |
| Changes ignored | Ensure you edited `goldfront-os/.env`, not dashboard `.env` only |
| 502 on domain | DNS/TLS not ready — use `curl http://127.0.0.1:8000/health` on box first |

---

## Related docs

- [MANUS-FINISH.md](./MANUS-FINISH.md) — deploy + verify on Manus
- [DEPLOY.md](./DEPLOY.md) — full deploy reference
- [reuse_manus_env.sh](./reuse_manus_env.sh) — auto-merge dashboard secrets
