# Connect Step-by-Step — Conrad Command Center / Superman Brain

**Last updated:** 2026-07-08  
**Env file:** `~/Documents/Claude/Projects/Brain/goldfront-os/.env`  
**Verify:** `curl -s http://127.0.0.1:8000/connectors/status | python3 -m json.tool`

Restart the Brain after any `.env` change.

---

## Legend

| Label | Meaning |
|-------|---------|
| **You do** | Manual steps in a browser or portal |
| **Echo does** | Automated once keys are in `.env` |
| **Paste this** | Copy value into `goldfront-os/.env` |

---

## 1. GoHighLevel (GHL) — ✅ Done

| | |
|---|---|
| **Status** | Connected |
| **Env vars** | `GHL_API_KEY`, `GHL_LOCATION_ID` |

**You do** (already completed):
1. GHL sub-account → **Settings → Private Integrations** → Create integration
2. Copy API key and Location ID from URL or settings

**Paste this:**
```
GHL_API_KEY=<your key>
GHL_LOCATION_ID=<your location id>
```

**Echo does:** CRM leads, unread texts, pipeline via `/ghl/crm`.

---

## 2. ClickUp — ✅ Done

| | |
|---|---|
| **Status** | Connected |
| **Env vars** | `CLICKUP_API_TOKEN`, `CLICKUP_WORKSPACE_ID` |

**You do** (already completed):
1. [ClickUp Settings → Apps](https://app.clickup.com/settings/apps) → Generate API Token
2. Workspace ID from Settings → Workspaces (`90141259054`)

**Paste this:**
```
CLICKUP_API_TOKEN=<token>
CLICKUP_WORKSPACE_ID=90141259054
CLICKUP_AUTO_SYNC=true
```

**Echo does:** Task routing, memory sync, issue-task from Echo Command.

---

## 3. Fieldy — ✅ Done

| | |
|---|---|
| **Status** | Connected |
| **Env vars** | `FIELDY_API_TOKEN` |

**You do** (already completed):
1. Copy token from Fieldy dashboard or existing Mac `.env`

**Paste this:**
```
FIELDY_API_TOKEN=<token>
FIELDY_API_BASE=https://api.fieldy.ai
FIELDY_SPEAKER_ME=Lindsey
```

**Echo does:** Meeting captures, conversation context for daily brief.

---

## 4. Anthropic / Echo — ✅ Done

| | |
|---|---|
| **Status** | Connected (test via `/chat`, not `/connectors/status`) |
| **Env vars** | `ANTHROPIC_API_KEY` |

**You do** (already completed):
1. [Anthropic Console → API Keys](https://console.anthropic.com/settings/keys) → Create key

**Paste this:**
```
ANTHROPIC_API_KEY=<sk-ant-...>
GOLDFRONT_OWNER=lindsey
```

**Echo does:** Live narration, drafts, deal math, operating brain.

---

## 5. Google Calendar + Gmail — ⏳ Needs setup

| | |
|---|---|
| **Status** | Not connected — `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` are **UNSET** |
| **Unlocks** | `google_calendar` + `gmail` (one OAuth app) |

### You do — Google Cloud Console

1. [Google Cloud Console](https://console.cloud.google.com/) → create/select project
2. **APIs & Services → Library** → enable **Google Calendar API** and **Gmail API**
3. **OAuth consent screen** → External → add your Gmail as test user
4. **Credentials → Create → OAuth client ID** → Desktop app
5. Edit client → Authorized redirect URIs → add:
   ```
   http://localhost:8765/oauth2callback
   ```
6. Copy Client ID and Client Secret

### Paste this

```
GOOGLE_CLIENT_ID=<id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<secret>
GOOGLE_CALENDAR_ID=primary
```

### You do — One-time OAuth

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
python3 scripts/google_oauth_setup.py
```

Script listens on **port 8765**, opens browser, writes `GOOGLE_REFRESH_TOKEN` to `.env`.

### Echo does

Calendar schedule + Gmail unread/recent threads (read-only).

---

## 6. Whoop — ⏳ Needs setup

| | |
|---|---|
| **Status** | Not connected — `WHOOP_CLIENT_ID`, `WHOOP_CLIENT_SECRET` are **UNSET** |

### You do — Whoop Developer Portal

1. [developer.whoop.com](https://developer.whoop.com) → create app
2. Redirect URI:
   ```
   http://localhost:8787/oauth2callback
   ```
3. Copy Client ID and Client Secret

### Paste this

```
WHOOP_CLIENT_ID=<id>
WHOOP_CLIENT_SECRET=<secret>
```

### You do — One-time OAuth

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
python3 scripts/whoop_oauth_setup.py
```

Script listens on **port 8787**, opens browser, writes `WHOOP_REFRESH_TOKEN` to `.env`.

### Echo does

Auto-refreshes tokens; displays recovery, HRV, sleep, strain. See [WHOOP-SETUP.md](./WHOOP-SETUP.md).

---

## 7. Apple Health — Skip

No cloud API. Optional `APPLE_HEALTH_EXPORT_PATH` to a local JSON export only.

---

## Current snapshot

| Connector | Status |
|-----------|--------|
| GHL | ✅ |
| ClickUp | ✅ |
| Fieldy | ✅ |
| Anthropic/Echo | ✅ |
| Google Calendar | ❌ |
| Gmail | ❌ |
| Whoop | ❌ |
| Apple Health | ⏭️ Skip |

**connected_count:** 3 of 7

---

## Env audit (no secrets printed)

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
for v in GHL_API_KEY GHL_LOCATION_ID CLICKUP_API_TOKEN CLICKUP_WORKSPACE_ID \
  FIELDY_API_TOKEN ANTHROPIC_API_KEY GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET \
  GOOGLE_REFRESH_TOKEN WHOOP_CLIENT_ID WHOOP_CLIENT_SECRET WHOOP_REFRESH_TOKEN; do
  if grep -q "^${v}=.\+" .env 2>/dev/null; then echo "$v=SET"; else echo "$v=UNSET"; fi
done
```
