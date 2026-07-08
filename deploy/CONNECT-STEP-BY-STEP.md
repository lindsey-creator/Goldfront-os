# Live JARVIS — Connect & Ship Checklist

Finish wiring the operating brain and ship the Live JARVIS command deck.

## Visual pass (done)

- Deep slate palette `#1a2332` / `#1e2a3a` — **no pure black**
- Glass panels `rgba(255,255,255,0.06)` + backdrop blur
- Live cyan `#00d4ff` / `#4ecdc4` — energy core, online dot, active states
- Gold `#c9a227` sparingly for Echo brand accents
- Animated `LiveCore` with cyan rings + poll flash on LIVE SIGNALS tiles
- Nav: **Dashboard | Echo | Stack**

## 1. `.env` audit (goldfront-os)

Run without printing secrets:

```bash
cd goldfront-os
python3 - <<'PY'
from pathlib import Path
keys = [
    "GOOGLE_CLIENT_ID","GOOGLE_CLIENT_SECRET","GOOGLE_REFRESH_TOKEN",
    "WHOOP_CLIENT_ID","WHOOP_CLIENT_SECRET","WHOOP_REFRESH_TOKEN",
    "GHL_API_KEY","GHL_LOCATION_ID","CLICKUP_API_TOKEN","FIELDY_API_TOKEN",
    "ANTHROPIC_API_KEY","META_ACCESS_TOKEN","WEATHER_API_KEY","APPLE_HEALTH_EXPORT_PATH",
]
env = {}
for line in Path(".env").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line: continue
    k, _, v = line.partition("=")
    env[k] = v
for k in keys:
    v = env.get(k, "")
    ok = v and v not in ("", "refresh_new", "changeme")
    print(f"{k}: {'SET' if ok else 'UNSET'}")
PY
```

| Variable | Purpose |
|----------|---------|
| `GHL_API_KEY` + `GHL_LOCATION_ID` | GoHighLevel CRM lane |
| `CLICKUP_API_TOKEN` | Tasks, Rhino Robot meetings |
| `FIELDY_API_TOKEN` | Daily brief + transcripts |
| `ANTHROPIC_API_KEY` | Echo chat / reasoning |
| `GOOGLE_CLIENT_ID` + `SECRET` + `REFRESH_TOKEN` | Calendar + Gmail |
| `WHOOP_CLIENT_ID` + `SECRET` + `REFRESH_TOKEN` | Health lane |
| `META_ACCESS_TOKEN` | Meta ads metrics |
| `WEATHER_API_KEY` | Weather tile |
| `APPLE_HEALTH_EXPORT_PATH` | Apple Health display |

## 2. Google OAuth (if `GOOGLE_CLIENT_ID` + `SECRET` set)

```bash
cd goldfront-os
python3 scripts/google_oauth_setup.py
```

Opens browser → grants Calendar (readonly) + Gmail (readonly) → writes `GOOGLE_REFRESH_TOKEN` to `.env`.

## 3. Whoop OAuth (if `WHOOP_CLIENT_ID` + `SECRET` set)

See `deploy/WHOOP-SETUP.md`, then:

```bash
cd goldfront-os
python3 scripts/whoop_oauth_setup.py
```

## 4. Build UI + restart brain

```bash
# From conrad-command-center
npm run build   # tsc -b && vite build

# Restart brain (pick one)
cd ../goldfront-os
pkill -f "uvicorn brain.main:app" 2>/dev/null || true
uvicorn brain.main:app --host 127.0.0.1 --port 8000 &
sleep 2
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/connectors/status | python3 -c "import sys,json; d=json.load(sys.stdin); print('connected_count:', d.get('connected_count'), '/', d.get('total'))"
```

On Manus/server: `sudo systemctl restart superman-brain`

## 5. Verify

| Check | Pass |
|-------|------|
| http://127.0.0.1:8000/ loads Live JARVIS deck | Slate bg, cyan core, no rhino horns |
| `JARVIS ONLINE` / `ECHO LIVE` breathing in header | Cyan glow when brain healthy |
| LIVE SIGNALS tiles flash on poll refresh | Cyan edge pulse |
| Intel lanes show GHL / ClickUp / Fieldy data | Data wiring intact |
| `connected_count` in `/connectors/status` | Report in terminal |

## 6. Tests + ship

```bash
cd goldfront-os && pytest -q
cd ../conrad-command-center && npm run build
git -C conrad-command-center add -A && git -C conrad-command-center commit -m "Live JARVIS executive finish — slate palette, no black"
git -C goldfront-os add -A && git -C goldfront-os commit -m "Live JARVIS executive finish — slate palette, no black"
git -C conrad-command-center push
git -C goldfront-os push
```

Open: **http://127.0.0.1:8000/** (Chrome Profile 10)
