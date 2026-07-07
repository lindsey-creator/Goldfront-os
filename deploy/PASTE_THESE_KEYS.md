# Paste these in chat (one at a time)

**Connector status:** 3/7 connected — ClickUp ✓ Fieldy ✓ GHL ✓

**Already set locally (skip):** `CLICKUP_API_TOKEN`, `FIELDY_API_TOKEN`

**Manus Fieldy:** copy `FIELDY_API_TOKEN` from Mac `goldfront-os/.env` — no new dashboard token.

---

Paste these **4** strings in chat, one message each:

1. **ANTHROPIC_API_KEY** — `sk-ant-...`  
   → https://console.anthropic.com/settings/keys (Create Key)

2. **GOOGLE_CLIENT_ID** — OAuth Desktop client  
   → https://console.cloud.google.com/apis/credentials

3. **GOOGLE_CLIENT_SECRET** — same OAuth client  
   → (after #2 + #3 saved, agent runs `python3 scripts/google_oauth_setup.py` for refresh token)

4. **WHOOP_ACCESS_TOKEN**  
   → https://developer.whoop.com/apps

---

After each paste: agent updates `.env` and restarts brain.

Verify: `curl -s http://127.0.0.1:8000/connectors/status`
