# Rhino Lending `/apply` — investigation (2026-09-11)

Read-only audit: whether **Goldfront-os** hosts or proxies `https://www.rhinolending.capital/apply`, and what it would take to add X Ads pixel `trackPid('rf7r4')` plus reliable GHL webhook `04f68c81` → location `3nUeqiIgQEtLuQJUbWVO`.

## Executive answer

| Question | Answer |
|----------|--------|
| Does **this repo** contain the `/apply` SPA/form? | **No.** |
| Does **this repo** proxy `www.rhinolending.capital`? | **No.** |
| Can pixel + webhook hardening be done **in this repo only**? | **No** — changes belong in the **Manus Rhino Capital web project** (space `M8WorjTm` / `rhinocap-m8worjtm.manus.space`), then republish. |
| Is GHL webhook `04f68c81` already wired on live `/apply`? | **Partially** — client-side fire-and-forget on **step 0 → 1 only**, not on full submit. Personal location `3nUeqiIgQEtLuQJUbWVO` is correct in the live bundle. |

---

## 1) Repo vs live site — file map

### This repository (`lindsey-creator/Goldfront-os`)

Purpose: **Superman Brain** (FastAPI) + deploy docs for **conradstrong.com** / command center — not the Rhino marketing site.

Relevant paths (none are `/apply`):

| Path | Role |
|------|------|
| `brain/main.py` | FastAPI; may mount **conrad-command-center** `dist/` when built — not Rhino Capital |
| `brain/connectors/ghl.py` | Read-only GHL API for cockpit (`GHL_LOCATION_ID` default **team** `FFdZCVGXSQQThtHZEOYx` in `.env.example`) |
| `deploy/nginx-*.conf` | Reverse proxy to `:8000` for Conrad domains only |
| `brain/operating/OPERATING_BRAIN.md` | Mentions domain `rhinolending.capital` in ops notes only |

No `index.html`, no Vite/React app for Rhino, no nginx/Caddy config for `rhinolending.capital`, no references to `rhinocap-m8worjtm`, webhook `04f68c81`, or X pixel `rf7r4`.

### Live production (observed 2026-09-11)

| Item | Value |
|------|--------|
| Money URL | `https://www.rhinolending.capital/apply` → **200** (SPA shell) |
| Apex | `https://rhinolending.capital/apply` → **405** (www required) |
| Host | Cloudflare → Manus (`x-manus-proxy-mode: transparent/1`, `x-powered-by: Express`) |
| Manus origin | `https://rhinocap-m8worjtm.manus.space/` (canonical/og in HTML still point here) |
| Client bundle | `/assets/index-b_wt0LWs.js` (hash may change on redeploy) |
| Analytics today | Manus Umami (`manus-analytics.com`) — **no** X/Twitter pixel in bundle |

Embedded source paths in the minified client (Manus project, **not in Goldfront-os**):

- `client/src/pages/Apply.tsx` — multi-step Non-QM apply wizard
- `client/src/pages/Contact.tsx` — contact page
- `client/src/pages/AdminLeads.tsx` — admin UI (`Ea.leads.*` tRPC)
- `client/src/App.tsx`, `client/src/main.tsx`, shared components

---

## 2) How form submission works today

### A) `/apply` — step 0 → 1 (early capture)

When the user leaves **Contact Info** (guarantor name + phone present), the client:

1. **GHL inbound webhook** (fire-and-forget, errors swallowed):

   ```
   POST https://services.leadconnectorhq.com/hooks/3nUeqiIgQEtLuQJUbWVO/webhook-trigger/04f68c81-381e-4bb5-a13a-2c9a059fa630
   Content-Type: application/json
   ```

   Body shape (from minified helpers `pB` / `mB`):

   | Field | Source |
   |-------|--------|
   | `email` | trimmed email |
   | `first_name` / `last_name` | split from `fullName` / guarantor name |
   | `phone` | trimmed phone |
   | `address` | property address (often empty at step 0) |
   | `city` | `""` |
   | `notes` | `"source: TLOC Shorts / rhinolending.capital/apply"` |

   **Tag requirement:** the string `rhinolending.capital/apply` appears only in **`notes`**, not a dedicated GHL `tags` array. Whether automation applies a contact tag depends on the **workflow** behind webhook `04f68c81` (verify in GHL UI).

   **Gaps:** requires `phone`; no retry; `.catch(() => {})`; does not run if user skips phone; does **not** run on final application submit.

2. **tRPC** `loanApply.saveLead` → `POST /api/trpc/loanApply.saveLead` with `{ guarantorName, email, phone? }` (partial save; server persists separately from GHL).

### B) `/apply` — final submit

`tRPC` `loanApply.submit` → `POST /api/trpc/loanApply.submit` with the full wizard payload (experience, loan type, property, financials, guarantor, etc.).

From the **client bundle only:** there is **no second** GHL webhook call on success. Any GHL sync on full submit would have to live in **Manus server** code (not present in Goldfront-os; not visible in the client bundle).

### C) `/contact`

Submit handler shows a toast only (`v6.success("Message sent!…")`) — **no** webhook, **no** API. Not production-ready for leads.

### D) Conrad Team GHL

Live apply webhook URL uses location **`3nUeqiIgQEtLuQJUbWVO`** (personal). This repo’s `.env.example` still defaults **`GHL_LOCATION_ID=FFdZCVGXSQQThtHZEOYx`** for Brain cockpit reads — unrelated to the public apply site.

### Phone on live site (FYI)

Structured data / footer / error copy use **`216-319-5782`**, not `216-250-9078`. No change made in this investigation.

---

## 3) Smallest PR plan (when editing the **Manus Rhino site** repo — not Goldfront-os)

Assuming the Manus project source that builds `client/src/pages/Apply.tsx`:

### (a) X Ads pixel `rf7r4` on `/apply` page load

1. In `client/index.html` **or** a small analytics module loaded once:
   - Standard X base pixel snippet + `twq('config','rf7r4');`
2. **Scope to `/apply` only** (recommended): in `Apply.tsx`, `useEffect` on mount call `twq('track','PageView')` or `trackPid` equivalent per [X Ads pixel docs](https://business.x.com/en/help/campaign-measurement-and-analytics/conversion-tracking-for-websites.html) — do **not** activate campaigns; pixel install only.
3. Redeploy Manus project; confirm `www.rhinolending.capital/apply` loads pixel (Network tab → `static.ads-twitter.com` / `t.co/i/adsct`).

**Do not** add pixel in Goldfront-os unless the site is moved behind Brain (it is not today).

### (b) Harden webhook + tag `rhinolending.capital/apply` on every successful submit

1. **Centralize** webhook URL in env (e.g. `VITE_GHL_APPLY_WEBHOOK`) — avoid hardcoding in client if possible; location must stay **`3nUeqiIgQEtLuQJUbWVO`**, webhook id **`04f68c81-381e-4bb5-a13a-2c9a059fa630`**.
2. **On `loanApply.submit` success** (and optionally keep step-0 capture):
   - `await fetch(webhook, { method: 'POST', … })` with full payload or mapped fields.
   - Send **`tags: ["rhinolending.capital/apply"]`** (or the exact key GHL workflow expects) **in addition to** `notes`, and align the GHL workflow to **add tag on webhook**.
3. **Failure handling:** surface user-visible error or server-side retry queue; log failures (today failures are silent).
4. **Server-side duplicate (best):** implement webhook POST in the **tRPC submit handler** on Manus server so ad blockers cannot drop the only copy.
5. **Verify** in personal GHL: test submit → contact created/tagged → workflow `04f68c81` runs.

### (c) Optional quick wins (same Manus PR)

- Fix `/contact` to use the same webhook or tRPC lead endpoint.
- Update canonical/og URLs to `https://www.rhinolending.capital/` when ready (separate from pixel/webhook; no DNS cutover invented here).

---

## 4) Stop line for Goldfront-os

**Do not rebuild the Rhino site in this repo.** Goldfront-os has no apply HTML/SPA and no proxy for `rhinolending.capital`. Next step is to locate the **Manus Rhino Capital project source** (Manus dashboard / export / linked Git repo), apply sections 3(a–b) there, and republish to space `M8WorjTm`.

---

## Verification commands (repeat audit)

```bash
curl -sI "https://www.rhinolending.capital/apply" | head
curl -sI "https://rhinolending.capital/apply" | head
curl -sL "https://www.rhinolending.capital/assets/index-b_wt0LWs.js" | rg -o 'leadconnectorhq.com/hooks[^"\']+'
curl -sL "https://www.rhinolending.capital/assets/index-b_wt0LWs.js" | rg 'twq|trackPid|rf7r4' || echo "no X pixel"
```

Replace `index-b_wt0LWs.js` with the current hashed filename from the `/apply` HTML shell after each deploy.
