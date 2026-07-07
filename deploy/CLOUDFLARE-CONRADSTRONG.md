# Cloudflare + Tunnel for conradstrong.com (Manus)

**Why this guide exists:** Manus runs Brain on `localhost:8000`, but **ports 80 and 443 are not exposed to the public internet** (Manus network restriction). A plain GoDaddy A record to `102.210.17.121` will not work — HTTPS times out.

**Permanent fix:** Cloudflare Tunnel (`cloudflared`) — outbound-only connection from Manus to Cloudflare. No inbound 80/443 required.

**Quick interim:** [trycloudflare quick tunnel](#alternative-ugly-trycloudflare-quick-tunnel-interim) (random URL, dies when the process stops).

| Item | Value |
|------|-------|
| Domain | `conradstrong.com` |
| Manus IP | `102.210.17.121` (local only; not reachable on 80/443) |
| App | `superman-brain` → `http://127.0.0.1:8000` |
| Tunnel script | `deploy/cloudflared-manus.sh` |

---

## Health check status (2026-07-07)

| URL | Result |
|-----|--------|
| `https://decided-watts-xhtml-disabilities.trycloudflare.com/health` | **200** — `{"status":"ok","service":"goldfront-brain"}` |
| `https://conradstrong.com/health` | **Timeout** — port 443 not reachable (expected until tunnel + DNS) |

---

## Step 1 — Sign up for Cloudflare

1. Go to [https://dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up).
2. Create an account (free plan is enough).
3. Verify your email.

---

## Step 2 — Add conradstrong.com to Cloudflare

1. In the Cloudflare dashboard, click **Add a site**.
2. Enter `conradstrong.com` → **Continue**.
3. Select the **Free** plan → **Continue**.
4. Cloudflare scans existing DNS records from GoDaddy. Review them — you can remove parking/forwarding records later.
5. **Do not change nameservers yet** — note the two nameservers Cloudflare shows (e.g. `ada.ns.cloudflare.com`, `bob.ns.cloudflare.com`). You need them in Step 3.

---

## Step 3 — Change GoDaddy nameservers to Cloudflare

1. Log in to [GoDaddy](https://www.godaddy.com/) → **My Products** → **DNS** for `conradstrong.com`.
2. Under **Nameservers**, choose **Change** → **Enter my own nameservers (advanced)**.
3. Replace GoDaddy nameservers with the two Cloudflare nameservers from Step 2.
4. Save. Propagation can take a few minutes to 48 hours (usually under an hour).
5. In Cloudflare, wait until the site shows **Active**.

---

## Step 4 — Set up Cloudflare Tunnel on Manus (recommended)

This is the real solution. Traffic flow:

```
Browser → Cloudflare edge (443) → cloudflared on Manus → localhost:8000
```

### 4a. Prerequisites on Manus

- Brain is running: `curl -sf http://127.0.0.1:8000/health`
- You can SSH or open a terminal on Manus.

### 4b. Run the install script

On **Manus** (Linux):

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os
git pull --ff-only
sudo bash deploy/cloudflared-manus.sh
```

The script will:

1. Install `cloudflared` (official Cloudflare package).
2. Open a browser URL for `cloudflared tunnel login` — log in as the Cloudflare account that owns `conradstrong.com`.
3. Create a named tunnel `conradstrong-brain`.
4. Write `/etc/cloudflared/config.yml` routing `conradstrong.com` and `www.conradstrong.com` → `http://127.0.0.1:8000`.
5. Install and enable `cloudflared` systemd service (starts on boot).

**Manual alternative** (if you prefer step-by-step): see comments in `deploy/cloudflared-manus.sh`.

### 4c. Route DNS through the tunnel (Cloudflare dashboard)

After the tunnel is created, Cloudflare needs CNAME records pointing at the tunnel:

1. Dashboard → **conradstrong.com** → **DNS** → **Records**.
2. Add (or let `cloudflared tunnel route dns` create):

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `@` | `<tunnel-id>.cfargotunnel.com` | Proxied (orange cloud) |
| CNAME | `www` | `<tunnel-id>.cfargotunnel.com` | Proxied |

The install script runs `cloudflared tunnel route dns conradstrong-brain conradstrong.com` and `... www.conradstrong.com` automatically when possible.

**Remove** any old A record pointing `@` to `102.210.17.121` — it conflicts with the tunnel and will not work anyway.

---

## Step 5 — SSL/TLS mode: Full

1. Cloudflare dashboard → **conradstrong.com** → **SSL/TLS** → **Overview**.
2. Set encryption mode to **Full** (not Flexible).
   - **Full** — Cloudflare ↔ origin uses HTTPS or, for tunnel, encrypted tunnel to `cloudflared` (recommended).
   - **Flexible** — can cause redirect loops with apps that expect HTTPS.
3. For tunnel-only setups, **Full** is correct; you do not need a cert on Manus for public traffic (tunnel handles it).

Optional: **SSL/TLS** → **Edge Certificates** → enable **Always Use HTTPS**.

---

## Step 6 — Verify

From any machine:

```bash
curl -sf https://conradstrong.com/health | python3 -m json.tool
curl -sf https://www.conradstrong.com/health | python3 -m json.tool
```

Expected:

```json
{
    "status": "ok",
    "service": "goldfront-brain"
}
```

On Manus:

```bash
sudo systemctl status cloudflared --no-pager
sudo journalctl -u cloudflared -n 30 --no-pager
curl -sf http://127.0.0.1:8000/health
```

Open in browser: [https://conradstrong.com](https://conradstrong.com) — Command Center UI should load.

---

## Troubleshooting

| Symptom | Check |
|---------|--------|
| `conradstrong.com` still times out | Nameservers still on GoDaddy? DNS only A record to Manus IP? |
| 502 / 1033 from Cloudflare | `superman-brain` down? `curl localhost:8000/health` on Manus |
| Tunnel not connecting | `sudo journalctl -u cloudflared -f` — re-run `cloudflared tunnel login` if creds expired |
| Wrong site / SSL error | SSL mode should be **Full**; purge Cloudflare cache |

---

## Alternative: ugly trycloudflare quick tunnel (interim)

Use this **only** until the permanent tunnel is live. URL changes every time; process must stay running.

On Manus:

```bash
# Brain must be up on :8000
curl -sf http://127.0.0.1:8000/health

# Install cloudflared if missing (see cloudflared-manus.sh), then:
cloudflared tunnel --url http://127.0.0.1:8000
```

Cloudflared prints a random URL, e.g.:

```
https://decided-watts-xhtml-disabilities.trycloudflare.com
```

Test:

```bash
curl -sf https://decided-watts-xhtml-disabilities.trycloudflare.com/health
```

**Downsides:**

- Random subdomain — not `conradstrong.com`
- Dies when terminal closes (unless you `nohup` / `screen` it)
- No SLA, not for production
- Good for proving Brain works through Cloudflare while you set up the real tunnel

**Current working interim URL (2026-07-07):**  
`https://decided-watts-xhtml-disabilities.trycloudflare.com/health` → 200 OK

---

## Summary checklist for Lindsey

- [ ] Cloudflare account + `conradstrong.com` added
- [ ] GoDaddy nameservers → Cloudflare
- [ ] `sudo bash deploy/cloudflared-manus.sh` on Manus
- [ ] DNS CNAMEs for `@` and `www` → tunnel (not A → Manus IP)
- [ ] SSL/TLS mode **Full**
- [ ] `https://conradstrong.com/health` returns 200

See also: `deploy/CONRADSTRONG-DEPLOY.md` (app deploy on Manus), `deploy/cloudflared-manus.sh` (tunnel automation).
