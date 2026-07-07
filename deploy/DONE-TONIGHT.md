# Done tonight (before Cloudflare)

Completed **2026-07-07** — everything except Cloudflare + `conradstrong.com` DNS.

## Manus: get latest UI + Brain

One command on Manus:

```bash
bash ~/Documents/Claude/Projects/Brain/goldfront-os/deploy/sync_manus_tonight.sh
```

Equivalent manual:

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os && git pull
cd ~/Documents/Claude/Projects/Brain/conrad-command-center && git pull && npm run build
sudo systemctl restart superman-brain
```

## Open now

| URL | What |
|-----|------|
| **http://127.0.0.1:8000/** | Echo command deck (Brain serves built `dist/`) |
| **https://decided-watts-xhtml-disabilities.trycloudflare.com/** | Interim quick tunnel (if process still running on Manus) |

Verify API:

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/chat -H 'Content-Type: application/json' -d '{"message":"ping"}'
```

## What's done

- **Echo command deck visual overhaul** — hero Rhino Core (128px), gold wordmark, priority horns, 4 intel lanes, obsidian/gold HUD, live indicator, mobile accordion
- **Brain serves UI** on port 8000 via `uvicorn brain.main:app` (not Vite preview alone)
- **Connectors 3/7 local:** ClickUp ✓ Fieldy ✓ GHL ✓
- **Echo /chat** works (fallback mode without Anthropic key; honest note returned)
- **pytest** goldfront-os — all pass
- **Fieldy docs** — user-token-only: copy `FIELDY_API_TOKEN` from Mac `.env`, no new dashboard token
- **Commits pushed** to `goldfront-os` + `conrad-command-center`

## Tomorrow only

See **`deploy/TOMORROW-CLOUDFLARE.md`** — Cloudflare Tunnel + DNS for `conradstrong.com`.

## Optional later

- Anthropic API key (live Echo voice narration)
- Google OAuth (calendar + Gmail)
- Whoop token (health lane)
