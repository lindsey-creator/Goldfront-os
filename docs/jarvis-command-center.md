# JARVIS Command Center — Brain as the live glass

**Goldfront OS (Brain)** is the API and reasoning layer. **JARVIS Command Center** is the
primary operator interface — the live glass Lindsey uses day to day.

| Piece | Repo / host | Role |
|-------|-------------|------|
| **Brain** | [lindsey-creator/Goldfront-os](https://github.com/lindsey-creator/Goldfront-os) | FastAPI: cockpit reads, `/chat`, connectors, deterministic deal engine |
| **Command Center UI** | [lindsey-creator/conrad-command-center](https://github.com/lindsey-creator/conrad-command-center) | React app; built to `dist/` and served by Brain on Manus |
| **Apply site** | Manus (separate stack) | `rhinolending.capital/apply` — **not** rebuilt from this repo |

On Manus, one process on port **8000** serves both: static UI at `/` and Brain routes under the
same origin (see `deploy/manus/README.md`). The UI talks to Brain via `VITE_BRAIN_API` (often
empty in production so the browser uses same-origin).

## JARVIS (sole command)

In product language, the combined strategist + ops partner behind the glass is **JARVIS**
(Jarvis / Grok Bot in chat). Legacy names (**Echo**, **CoS**, **Fable**) referred to the same
lane — use **JARVIS** in user-facing copy and new docs.

Operating context and hard rules still load from `brain/operating/OPERATING_BRAIN.md`.

## Connect the UI to Brain (local dev)

```bash
# Terminal 1 — Brain
cd goldfront-os && source .venv/bin/activate
uvicorn brain.main:app --reload --port 8000

# Terminal 2 — UI (from conrad-command-center clone)
cd conrad-command-center
echo 'VITE_BRAIN_API=http://127.0.0.1:8000' > .env.local
npm install && npm run dev
```

Production on Manus: build UI (`npm run build`), place repo sibling to `goldfront-os`, restart
Brain — it mounts `../conrad-command-center/dist` automatically (`brain/main.py`).

## “JARVIS live” indicator (no fake data)

Use **`GET /health`** for a cheap liveness check (200 + JSON). Example:

```json
{
  "status": "ok",
  "service": "goldfront-brain",
  "command": "jarvis",
  "glass": "conrad-command-center",
  "ui_built": true,
  "engines": {"claude": true, "grok": true, "muse": false},
  "xai": true,
  "anthropic": true
}
```

- `ui_built` is `true` when `conrad-command-center/dist` exists on the server (glass can load).
- `engines` / `xai` / `anthropic` are **presence flags only** (no secret values). HUD chips
  use these so Grok does not stay “need API key” when `XAI_API_KEY` is set.
- `POST /chat` accepts `{"message","model"}` where `model` is `claude` (default), `grok`, or
  `muse` (case-insensitive). Missing Grok/Muse credentials return an honest error — never
  a fake Claude reply.
- For connector readiness (GHL, ClickUp, etc.), use **`GET /connectors/status`** — never invent
  business metrics in the health payload.

CORS already allows `conradstrong.com` and `command*.theconradteam.com` origins (`brain/main.py`).

## GoHighLevel location IDs (do not mix)

| Location | ID | Use |
|----------|-----|-----|
| **Team (The Conrad Team)** | `FFdZCVGXSQQThtHZEOYx` | Brain `GHL_LOCATION_ID` for team CRM reads via API |
| **Personal (apply capture)** | `3nUeqiIgQEtLuQJUbWVO` | `rhinolending.capital/apply` lead capture — **not** the Brain write target |

**Rule:** Never point Brain automation or API writes at the personal apply sub-account by mistake.
Brain should use **Team `FFdZ…`** for Conrad team CRM. The personal location is for apply-site
capture only (see `deploy/FINISH-ALL.md`).

Copy `goldfront-os/.env.example` → `.env` on Manus only; never commit secrets.

## Lindsey Conrad

Lindsey Conrad uses **he/him**. Keep docs and operator-facing copy aligned.

## Related

- Experience modules: `docs/command-center-experience.md`
- Deploy: `deploy/DEPLOY.md`, `deploy/RAILWAY.md`, `deploy/manus/README.md`
- Master product spec: `docs/master-spec.md`
