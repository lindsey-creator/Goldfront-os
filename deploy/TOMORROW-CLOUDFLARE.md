# Tomorrow: Cloudflare only (Lindsey)

Everything else is done tonight. **Only** DNS + Cloudflare Tunnel remain for `conradstrong.com`.

## Prerequisites

- Cloudflare account owns **conradstrong.com**
- Manus box has Brain running: `http://127.0.0.1:8000/health` → `{"status":"ok"}`
- Latest UI pulled: `bash deploy/sync_manus_tonight.sh` (or manual pull + build)

## Steps (on Manus)

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
sudo bash deploy/cloudflared-manus.sh
```

This script:

1. Installs `cloudflared`
2. Opens browser for `cloudflared tunnel login` (Cloudflare account)
3. Creates tunnel `conradstrong-brain`
4. Routes `conradstrong.com` + `www.conradstrong.com` → `http://127.0.0.1:8000`
5. Enables `cloudflared` systemd service

## DNS (Cloudflare dashboard)

**Remove** any A record pointing `@` → Manus IP (`102.210.17.121`).

**Add** (or let the script create):

| Type  | Name | Target                         | Proxy   |
|-------|------|--------------------------------|---------|
| CNAME | `@`  | `<tunnel-id>.cfargotunnel.com` | Proxied |
| CNAME | `www`| `<tunnel-id>.cfargotunnel.com` | Proxied |

SSL/TLS mode: **Full** (recommended for tunnel).

## Verify

```bash
curl -sf https://conradstrong.com/health
curl -sf https://conradstrong.com/connectors/status
```

Open **https://conradstrong.com/** — Echo command deck with Rhino Core, priority horns, intel lanes.

## If something breaks

```bash
sudo systemctl status cloudflared superman-brain --no-pager
sudo journalctl -u cloudflared -n 40 --no-pager
sudo journalctl -u superman-brain -n 40 --no-pager
```

Full reference: `deploy/CLOUDFLARE-CONRADSTRONG.md`

## Optional later (not required for launch)

- `ANTHROPIC_API_KEY` — live Echo narration (fallback works without it)
- Google OAuth — Calendar + Gmail lanes
- `WHOOP_ACCESS_TOKEN` — health metrics lane
