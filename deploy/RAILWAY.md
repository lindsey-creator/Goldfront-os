# Deploy JARVIS Command Center on Railway

**Type-1 path:** one Railway service runs **Goldfront-os Brain** (FastAPI) and serves the **built Conrad Command Center UI** (Iron Man HUD from `lindsey-creator/conrad-command-center` `main`). **No Manus** as primary host.

**Architecture one-liner:** **Jarvis (this Command Center on Railway) = glass + sole command. Desks/Town/GHL/mail feed Jarvis. Cursor = code factory. No second chiefs.**

All systems run through **Cursor-built JARVIS** — the sole command glass on Railway.

---

## Locked architecture

| Piece | Where |
|-------|--------|
| Brain API + static UI | Single process: `uvicorn brain.main:app` on `$PORT` |
| UI assets | Built at Docker build time from public GitHub [`conrad-command-center`](https://github.com/lindsey-creator/conrad-command-center.git) `main` → `/app/conrad-command-center/dist` |
| Path resolution | Same as Manus: `brain/main.py` mounts sibling `../conrad-command-center/dist` (see `deploy/manus/Dockerfile` / `deploy/build_and_run.sh`) |
| Health | `GET /health` → `status=ok`, `command=jarvis` (also `glass`, `ui_built`) |
| Public URL | **`https://jarvis-brain-production-8def.up.railway.app`** — enough for production. Custom DNS is optional and not required. |
| Port | Service **`PORT=8000`** (Railway domain binding). Dockerfile defaults to 8000. |

Build artifacts in repo root:

- `Dockerfile` — multi-stage: Node builds UI, Python runs Brain
- `railway.toml` — Dockerfile builder + `/health` healthcheck
- `.dockerignore` — keeps image lean

**Out of scope for this deploy:** Manus scripts as primary path, GHL writes, fake connector data, ChatGPT as a fleet connector, hosting Command Center on Manus.

---

## Connector map (everything feeds JARVIS)

Jarvis on Railway is the **only** command surface. Connectors are read paths into the Brain; the UI **Connections** module shows **Connect source** until env is live, then **Live**.

| # | System | Role on Railway | Brain / UI wiring | Env / notes |
|---|--------|-----------------|-------------------|-------------|
| 1 | **Town.com** | Relationship / mail **radar only** (no auto-send) | Do **not** rebuild Town in Railway. Digests from `rhino@town.com` land in **`lindsey@theconradteam.com` Gmail** → Brain reads mail via **Gmail connector** (Superhuman is the human client; Brain uses Google OAuth). Jarvis surfaces Type-1s from ingest. **Town radar** = UI module slot: **Connect source** until Gmail is **Live**. | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` (Gmail scope) |
| 2 | **Team GHL** | CRM module (**read**) | `ghl` connector → Connections → GoHighLevel | `GHL_API_KEY`, `GHL_LOCATION_ID=FFdZCVGXSQQThtHZEOYx` (Team CRM). Personal apply `3nUeqi…` is **not** the Brain write target — see `docs/jarvis-command-center.md`. |
| 3 | **Google** | Calendar, Gmail, Drive reads | `google_calendar`, `gmail` (+ Drive via same OAuth where used) | Same OAuth trio + `GOOGLE_CALENDAR_ID`; set `GOOGLE_OAUTH_REDIRECT_URI` to your **public Jarvis URL** (see below) |
| 4 | **WHOOP** | Health metrics | `whoop` connector | `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET`, `WHOOP_REFRESH_TOKEN` — see [WHOOP-SETUP.md](./WHOOP-SETUP.md) |
| 5 | **Meta Ads** | Spend / leads / CPL read | `meta` connector | `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID` |
| 6 | **ClickUp** | Tasks + memory sync | `clickup` connector | `CLICKUP_API_TOKEN`, `CLICKUP_WORKSPACE_ID` (default `90141259054`), optional `CLICKUP_AUTO_SYNC=true` |
| 7 | **Plaud / Fieldy** | Commitments via Meeting-to-Action → Jarvis | **Fieldy** API + ClickUp ingest routes (`fieldy`, Plaud/Fieldy metadata in ClickUp routing). Some flows may be **agent-fed** (Cursor/Manus named builds) rather than a live Brain API — document in runbooks; do not fake meeting data. | `FIELDY_API_TOKEN`, `FIELDY_API_BASE`, `FIELDY_SPEAKER_ME` |
| 8 | **Wispr Flow** | OS voice into JARVIS command line | **No API.** See [docs/WISPR-FLOW-JARVIS.md](../docs/WISPR-FLOW-JARVIS.md) | — |
| 9 | **Manus** | Named builds / legacy box only | **Not** Command Center hosting. Use for one-off scripts or old tunnel only during cutover. | — |
| 10 | **ChatGPT** | Human-only | Not a fleet connector | — |
| 11 | **Claude** | Strategy lane; reports **to** Jarvis, not a second chief | `/chat` when `ANTHROPIC_API_KEY` set; reasoning narrates, does not replace Jarvis glass | `ANTHROPIC_API_KEY` |

Optional: `WEATHER_API_KEY`, `APPLE_HEALTH_EXPORT_PATH` (display-only file path — not typical on Railway), `CLICKUP_MCP_URL`, `DECISION_HALFLIFE_DAYS`.

Full connector checklist and Manus-oriented steps still apply for **secrets sourcing**: [CONNECT-EVERYTHING.md](./CONNECT-EVERYTHING.md).

---

## 1. Create Railway project + connect GitHub (< 5 min)

1. Sign in at [railway.app](https://railway.app) (GitHub OAuth).
2. **New Project** → **Deploy from GitHub repo**.
3. Select **`lindsey-creator/Goldfront-os`** (authorize Railway GitHub app if prompted).
4. Use branch **`master`**.
5. Railway reads **`railway.toml`** and builds with root **`Dockerfile`** (do not switch to Railpack/Nixpacks — master has no Railpack start command).
6. Set service **`PORT=8000`**. First deploy may fail until env vars exist — add vars in step 2 and redeploy.

**If GitHub connect is blocked:** Project → **Settings** → connect repository manually; ensure Railway has read access to `Goldfront-os`.

---

## 2. Environment variables (required names only — never commit values)

In Railway → your service → **Variables**, paste from local `.env` / `.env.example`. **Do not invent secrets in docs or chat.**

### Core (set on every deploy)

| Variable | Purpose |
|----------|---------|
| `GOLDFRONT_OWNER` | `lindsey` — private brain owner |
| `ANTHROPIC_API_KEY` | Live `/chat` (Claude lane to Jarvis) |

### Connectors (add what you use)

| Variable | Connector |
|----------|-----------|
| `CLICKUP_API_TOKEN` | ClickUp |
| `CLICKUP_WORKSPACE_ID` | ClickUp (default `90141259054`) |
| `CLICKUP_AUTO_SYNC` | ClickUp sync (`true` typical) |
| `GHL_API_KEY` | Team GHL read |
| `GHL_LOCATION_ID` | **`FFdZCVGXSQQThtHZEOYx`** Team CRM — not personal apply `3nUeqi…` |
| `GOOGLE_CLIENT_ID` | Google Calendar + Gmail |
| `GOOGLE_CLIENT_SECRET` | Google Calendar + Gmail |
| `GOOGLE_REFRESH_TOKEN` | Google Calendar + Gmail |
| `GOOGLE_CALENDAR_ID` | Usually `primary` |
| `GOOGLE_OAUTH_REDIRECT_URI` | **`https://jarvis-brain-production-8def.up.railway.app/google/oauth/callback`** |
| `WHOOP_CLIENT_ID` | WHOOP |
| `WHOOP_CLIENT_SECRET` | WHOOP |
| `WHOOP_REFRESH_TOKEN` | WHOOP |
| `META_ACCESS_TOKEN` | Meta Ads |
| `META_AD_ACCOUNT_ID` | Meta Ads |
| `FIELDY_API_TOKEN` | Fieldy / meeting ingest |
| `FIELDY_API_BASE` | Default `https://api.fieldy.ai` |
| `FIELDY_SPEAKER_ME` | e.g. `Lindsey` |
| `WEATHER_API_KEY` | Optional weather module |
| `APPLE_HEALTH_EXPORT_PATH` | Optional; rarely used on Railway |

Copy template from repo **`.env.example`** and [CONNECT-EVERYTHING.md](./CONNECT-EVERYTHING.md). Source real values from the Mac `.env` or approved secret store.

After any variable change: Railway redeploys automatically (or click **Redeploy**).

---

## 3. After deploy — modules flip **Connect source** → **Live**

1. Open Jarvis URL (`https://jarvis-brain-production-8def.up.railway.app/`).
2. Go to **Connections** (Command Center UI).
3. Each row shows **Connect source** until Brain sees required env vars.
4. When vars are set and redeploy finished, refresh → connector shows **Live** (backed by `GET /connectors/status`).

Verify from terminal:

```bash
curl -sf "https://jarvis-brain-production-8def.up.railway.app/health" | python3 -m json.tool
curl -sf "https://jarvis-brain-production-8def.up.railway.app/connectors/status" | python3 -m json.tool
```

| UI module | `connected: true` when |
|-----------|-------------------------|
| GoHighLevel | `GHL_API_KEY` + Team `GHL_LOCATION_ID` |
| Gmail (+ Town radar ingest) | Google OAuth trio |
| Google Calendar | Same Google OAuth trio |
| ClickUp | Token + workspace ID |
| Fieldy | `FIELDY_API_TOKEN` |
| WHOOP | OAuth trio (or legacy token — prefer OAuth) |
| Meta Ads | `META_ACCESS_TOKEN` + `META_AD_ACCOUNT_ID` |
| Town radar slot | Gmail **Live** + mail ingest path documented; no Town API in Railway |

**Anthropic** is not listed in `/connectors/status` — test `/chat` or Connections narration.

---

## 4. Public URL (no custom DNS required)

Production URL: **`https://jarvis-brain-production-8def.up.railway.app`**.

Confirm:

```bash
curl -sf "https://jarvis-brain-production-8def.up.railway.app/health" | python3 -m json.tool
```

Expect `"status":"ok"` and `"command":"jarvis"`. Custom domains are optional and out of scope.

Update **Google Cloud OAuth** authorized redirect URIs to include that Railway hostname if Google connect is used.

---

## 5. Railway CLI (optional)

CLI was **not** authenticated in the agent environment. To deploy from a laptop:

```bash
npm i -g @railway/cli
railway login          # opens browser — Lindsey must authorize
cd path/to/Goldfront-os
railway link           # pick the JARVIS project + service
railway variables      # set env (or use dashboard)
railway up             # deploy current directory (uses Dockerfile)
railway domain         # add custom domains
```

Without `railway login`, use the **Railway dashboard** only — fully sufficient for this recipe.

---

## 6. Wispr Flow (voice)

Iron Man voice input is **OS-level dictation** into the JARVIS command line on Lindsey's machine (Revolution One), not a Railway API. See **[docs/WISPR-FLOW-JARVIS.md](../docs/WISPR-FLOW-JARVIS.md)**.

---

## 7. Smoke checklist (human, < 15 min once logged in)

- [ ] GitHub repo connected; deploy from `master`
- [ ] `PORT=8000` set on the service
- [ ] Variables pasted from `.env` (Team GHL ID, Google, WHOOP, Meta, ClickUp, Fieldy, Anthropic)
- [ ] `https://jarvis-brain-production-8def.up.railway.app/health` shows `"command":"jarvis"`
- [ ] `/` loads Iron Man HUD (not JSON error)
- [ ] Connections modules move to **Live** as keys validate

---

## Related docs

| Doc | Use |
|-----|-----|
| [CONNECT-EVERYTHING.md](./CONNECT-EVERYTHING.md) | Env sourcing, connector order, verify commands |
| [WHOOP-SETUP.md](./WHOOP-SETUP.md) | WHOOP OAuth on Brain |
| [DEPLOY.md](./DEPLOY.md) | Legacy Manus layout (reference only) |
| [nginx-conradstrong.com.conf](./nginx-conradstrong.com.conf) | Hostname alias list for parity |
