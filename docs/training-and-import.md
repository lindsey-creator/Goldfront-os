# Training & Import — how to feed the Brain

This is build-sequence **step 2** (master spec §5.5, §10): teach the Brain your
voice, your deal instincts, and how you handle people — so it's *you*, not a
template. Nothing here computes deal money; all arithmetic still runs through the
deterministic engine (§3.1).

Everything below runs with **no API key and no ChromaDB** thanks to a JSON memory
fallback. When you're ready for real vector memory, just `pip install chromadb`
and set `ANTHROPIC_API_KEY` for smarter auto-classification — the code switches
automatically.

---

## 0. One-time setup

```bash
cd goldfront-os
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q            # 40 tests should pass
```

Run the API:

```bash
uvicorn brain.main:app --reload
# http://127.0.0.1:8000/docs  ← interactive UI for every endpoint below
```

Memory backend selection (optional):
- default: uses ChromaDB if installed, else a JSON store under `./.memory`
- force JSON: `export GOLDFRONT_MEMORY_BACKEND=json`
- smarter classification: `export ANTHROPIC_API_KEY=sk-...`

---

## 1. Bulk message import — paste 50 at once

Feeds your real messages (texts, emails, Slack) into **voice** training. Missing
metadata is auto-classified (recipient + context).

Formats: `.txt` (one per line, or blank-line-separated), `.csv`, `.json`, `.jsonl`.

```bash
# a plain text dump, one message per line
python -m brain.training.importers.bulk_messages samples/messages.txt

# a CSV with columns: message, recipient, context (any of them optional)
python -m brain.training.importers.bulk_messages samples/messages.csv

# paste straight from your clipboard via stdin
pbpaste | python -m brain.training.importers.bulk_messages - --source texts
```

CSV column names are flexible (case-insensitive):
`message`/`text`/`body` → the message · `to`/`recipient` → who · `context`/`category` → situation.

---

## 2. Deal-decision training + history

Paste a deal you evaluated and your verdict. It stores the example, runs the
rules engine in parallel, and **flags divergence** when your gut contradicts your
own rules.

```bash
curl -X POST localhost:8000/train/deal-decision -H 'Content-Type: application/json' -d '{
  "address": "123 Maple, Akron",
  "purchase_price": 90000, "arv": 200000, "rehab_estimate": 35000,
  "monthly_rent": 1800, "monthly_debt_service": 1100,
  "verdict": "GO",
  "reasoning": "Baker loves the comps; DSCR is clean and it opens the flywheel."
}'
```

See everything you've trained (newest first, recency-weighted):

```bash
curl localhost:8000/decisions/history
curl "localhost:8000/decisions/history?verdict=NO-GO&limit=20"
```

Flips with no rent/debt-service are fine — the Brain records the decision and
notes DSCR wasn't computed (best a margin-only deal earns from the rules is
CONDITIONAL).

---

## 3. Team-interaction training

```bash
curl -X POST localhost:8000/train/team-interaction -H 'Content-Type: application/json' -d '{
  "person": "Aaron",
  "situation": "Asked how to structure the Titus DSCR + modular ADU",
  "response": "Told him to lead with the flywheel math, hold margin at 30%, loop Baker on comps.",
  "category": "coaching"
}'
```

`category` is optional — omit it and it's auto-classified into one of:
coaching, accountability, praise, delegation, correction, firing.

---

## 4. Apollo import

**Export from Apollo:**
1. In Apollo, open the list/sequence with the contacts and outreach you want.
2. Select the records (or the whole list).
3. **Export → CSV.** Include, if offered: contact name, email, company, title,
   email/message body (your sent message), and reply/response, subject.
4. You'll get a `.csv` by email or download.

**Feed it in:**

```bash
python -m brain.training.importers.apollo ~/Downloads/apollo_export.csv
```

It routes **your sent messages → voice** and the **full exchange →
conversation_patterns** (so the Brain learns how you qualify, handle objections,
and close). Column names are matched flexibly, so Apollo's exact export headers
don't need to match anything — common variants are handled.

---

## 5. ClickUp & Fieldy (live inside Cowork)

"ClickUp has all my brain stuff" and "watch Fieldy daily" are wired as adapters
in `brain/training/importers/clickup_ingest.py` and `fieldy_ingest.py`.

Both pull *live* data through their MCP connectors, which only work in an
**authorized Cowork session** (OAuth can't run in a headless build). The routing
logic is built and tested against sample data; to go live, run them from Cowork
with ClickUp and Fieldy connected. A daily scheduled task can call the Fieldy
adapter each morning over the previous day's window — that's the "watch it" part.

---

## Where the data lives

- JSON backend: `./.memory/{voice,decisions,conversation_patterns,knowledge}.json`
- ChromaDB backend: `./.chroma/`

Both are git-ignored. This is your data — keep it local.
