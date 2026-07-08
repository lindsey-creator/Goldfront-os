# Whoop Setup — Persistent Connection (No Disconnects)

Whoop access tokens expire in about an hour. A static `WHOOP_ACCESS_TOKEN` in `.env` will stop working and the Brain will show Whoop as disconnected.

**Fix:** OAuth with the `offline` scope + a refresh token. The Brain refreshes automatically before each API call and rotates the refresh token in `.env` when Whoop issues a new one.

---

## 1. Register an app

1. Go to [developer.whoop.com](https://developer.whoop.com) and sign in with your Whoop account.
2. Create a new app (e.g. **Conrad Brain**).
3. Add this **Redirect URI** exactly:
   ```
   http://localhost:8787/oauth2callback
   ```
4. Copy **Client ID** and **Client Secret** — you will need them in step 3.

---

## 2. Scopes needed for health metrics

The Brain reads recovery, HRV, sleep, and strain (display only). Request these scopes:

| Scope | Purpose |
|-------|---------|
| `offline` | **Required** — gives you a refresh token |
| `read:recovery` | Recovery score, HRV, resting HR |
| `read:cycles` | Strain / day strain |
| `read:sleep` | Sleep duration |
| `read:workout` | Workout context (optional but useful) |
| `read:profile` | Basic profile |

The setup script requests all of these automatically.

---

## 3. One-time browser OAuth (Mac)

On your Mac, in `goldfront-os`:

```bash
cd ~/Documents/Claude/Projects/Brain/goldfront-os

# Add client credentials to .env first (or enter when prompted):
# WHOOP_CLIENT_ID=...
# WHOOP_CLIENT_SECRET=...

python3 scripts/whoop_oauth_setup.py
```

What happens:

1. Browser opens → log in to Whoop → approve scopes.
2. Callback hits `localhost:8787` → script exchanges the code for tokens.
3. Script writes to `.env` (values never printed):
   - `WHOOP_CLIENT_ID`
   - `WHOOP_CLIENT_SECRET`
   - `WHOOP_REFRESH_TOKEN`
   - `WHOOP_ACCESS_TOKEN` (initial; Brain refreshes this automatically)

Restart the Brain locally to verify:

```bash
curl -s http://127.0.0.1:8000/connectors/status | python3 -m json.tool
# whoop.connected should be true
```

---

## 4. How auto-refresh works (so it does not disconnect)

`brain/connectors/whoop_auth.py`:

1. On each Whoop API call, checks an in-memory cache (expires ~1 hour minus 60s buffer).
2. If expired, POSTs to `https://api.prod.whoop.com/oauth/oauth2/token` with:
   - `grant_type=refresh_token`
   - `refresh_token`, `client_id`, `client_secret`, `scope=offline`
3. Whoop returns a **new** access token and often a **new** refresh token (single-use rotation).
4. The new refresh token is written back to `.env` automatically.

You do **not** need to re-run the browser flow unless you revoke the app or delete the refresh token.

**Legacy:** If you only have `WHOOP_ACCESS_TOKEN` (no OAuth trio), it still works but will expire — migrate to OAuth.

---

## 5. What to add on Manus `.env`

Copy these four vars from your Mac `goldfront-os/.env` to Manus:

```bash
WHOOP_CLIENT_ID=
WHOOP_CLIENT_SECRET=
WHOOP_REFRESH_TOKEN=
# WHOOP_ACCESS_TOKEN=   # optional — Brain refreshes from refresh token
```

Path on Manus:

```
~/Documents/Claude/Projects/Brain/goldfront-os/.env
```

Then restart:

```bash
sudo systemctl restart superman-brain
curl -sf http://127.0.0.1:8000/connectors/status | python3 -m json.tool
```

Do **not** commit `.env`. Copy secrets privately (1Password, secure paste on Manus).

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `401 Unauthorized` on recovery | Re-run `whoop_oauth_setup.py` or paste a fresh `WHOOP_REFRESH_TOKEN` |
| No refresh token after OAuth | Ensure `offline` scope was requested (setup script includes it) |
| Redirect URI mismatch | Register `http://localhost:8787/oauth2callback` in Whoop dashboard |
| Whoop shows disconnected after ~1h | You are on legacy `WHOOP_ACCESS_TOKEN` only — complete OAuth setup |

---

## Related docs

- [CONNECT-EVERYTHING.md](./CONNECT-EVERYTHING.md) — full connector checklist
- [FINISH-ALL.md](./FINISH-ALL.md) — Manus deploy + env vars
