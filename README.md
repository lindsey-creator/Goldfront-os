# Goldfront OS

**One brain for the whole operation.** A private operating system that runs the
Conrad / Goldfront multi-vertical lending and construction business — holding the
deal rules, decision history, and voice of the operator, and using them to
evaluate deals, draft communications, brief daily, and train the team.

Full definition lives in [`docs/master-spec.md`](docs/master-spec.md). Read that first.

---

## The non-negotiables (see spec §3)

1. **The Brain narrates; it never computes.** All money math runs through the
   deterministic engine in `brain/engine/`. The AI explains numbers, it never calculates them.
2. **Internal-facing on anything credit-adjacent.** It recommends structure to
   licensed people; it never makes a credit decision to a borrower.
3. **Nothing sends without a human gate.** Drafts go to the Approval Queue.
4. **It escalates, it doesn't guess** on the novel calls.

---

## What works today

The deterministic engine and its API endpoint are real and tested. Everything
else is scaffolded with stubs that point at the spec section they implement.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

pytest                                   # engine tests should all pass
uvicorn brain.main:app --reload          # then POST to /evaluate-deal
```

---

## Structure

```
goldfront-os/
├── docs/master-spec.md      # single source of truth — read this
├── brain/                   # the core intelligence (the asset)
│   ├── config.py            # encoded thresholds — change rules HERE, one place
│   ├── main.py              # FastAPI app (/health, /evaluate-deal live)
│   ├── engine/              # deterministic math — REAL, tested, no AI
│   ├── memory/              # ChromaDB knowledge base (stub)
│   ├── persona/             # voice + decision framework (stub)
│   ├── agent/               # Claude reasoning agent (stub)
│   └── training/            # /train/* + divergence flagging (stub)
├── cockpit/                 # React front end (built after the Brain works)
└── tests/                   # engine tests
```

---

## Build sequence (do it in this order — spec §10)

1. Brain core — engine + memory + persona
2. Training loop — feed it your history so it's actually you
3. **Validation (shadow mode)** — match ~20 of your real past calls before it makes any. Do not skip.
4. Cockpit — on top of a Brain that already works
5. Deploy + integrations — server, OAuth for GHL/Gmail/Calendar, go live narrow

---

## Push this to your own GitHub

This repo is initialized and committed locally. Create an **empty** repo on
GitHub (no README), then:

```bash
git remote add origin https://github.com/<you>/goldfront-os.git
git branch -M main
git push -u origin main
```

## Open it in Cowork

Open the Cowork app, start a project on this folder, and point it at
`docs/master-spec.md` + this README. Tell it to build step 1 of the sequence.
