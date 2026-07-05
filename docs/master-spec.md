# Goldfront OS — Master Build Spec

*One brain for the whole operation. This document is the single source of truth. Everything that was scattered across three earlier build sessions lives here now, reconciled and corrected.*

---

## 0. Read this first

There is **one system**, not two. Earlier work called the intelligence layer "The Lindsey AI" and the interface "Goldfront OS." Those are the same system. From here on:

- **The Brain** = the core intelligence (memory, deal math, your voice, your decisions). It thinks.
- **The Cockpit** = the interface you and the team look at. It shows the Brain's work and gates what goes out.
- **Goldfront OS** = the whole thing, Brain + Cockpit, together.

If you ever want to rename the product, that's your call — flagged in §11.

---

## 1. What this is, in one paragraph

Goldfront OS is a private operating system that runs Lindsey Conrad's multi-vertical lending and construction operation. It holds your deal rules, your decision history, and your voice, and it uses them to evaluate deals, draft communications, brief you every morning, and train your team — in your voice, to your standards — so the business runs across markets without requiring you in the room. It never guesses on the things that matter. It escalates.

---

## 2. The business the Brain runs

Northeast Ohio, core markets **Cleveland / Akron / Canton**.

| Entity | Role |
|---|---|
| **Conrad Mortgage** | QM (qualified mortgage) lending |
| **Goldfront Capital** | Non-QM / DSCR lending + hard money |
| **Goldfront Homes** | Pre-fab / modular construction |
| **Rhino Network** | Coaching |
| **Stone Donut** | AI / automation (this system's home) |

Plus in-house or partnered: construction management, wholesale acquisition, title, insurance, property management.

**The flywheel — six touches on one relationship:**
`hard money → construction → title → insurance → DSCR refi → property management`

The point of the Brain is to see, for every deal, how many of those six touches are live and how much revenue the full flywheel represents — not just the loan in front of it.

**The team the Brain knows:**
Emma, Aaron (deal owners / LOs), Ken (capital partner), Gen, Ryan Baker (ARV & comps), Bobby (wholesale & construction), Brett (construction management), Tracy (title).

**Capital facts:** Joe's capital costs 10% + 1 point. Goldfront lends at 12–14% + 1–2 points. **CB3** is the preferred DSCR takeout lender.

---

## 3. Non-negotiable principles

These are hard constraints. They do not get traded away for convenience.

1. **The Brain narrates; it never computes.** All arithmetic — DSCR, margin, flywheel revenue — runs through a deterministic math engine. The language model explains the numbers, it does not calculate them. This is the difference between a tool you can trust with money and one you can't.
2. **Internal-facing on anything credit-adjacent.** The Brain can recommend loan structure to your licensed people. It never makes a credit decision to a borrower. That's licensed activity and a compliance problem waiting to happen. *(Not legal advice — this is the line to hold, and where you'd want counsel to confirm the specifics for your license setup.)*
3. **Nothing sends without a human gate.** Every AI-drafted message goes to the Approval Queue. You (or a delegated approver) approve, edit, or deny. The Brain never hits "send" on its own.
4. **It escalates, it doesn't guess.** The Brain handles the 80% of repeatable decisions. On the novel 20% it flags and hands to a human. Build it to know the difference.
5. **Recent decisions outweigh old ones.** Your instincts evolve. The memory weights recent calls more heavily (180-day half-life, tunable).

---

## 4. Architecture

```
┌───────────────────────────── GOLDFRONT OS ─────────────────────────────┐
│                                                                         │
│   COCKPIT (front end)                 BRAIN (core service)              │
│   ────────────────────                ────────────────────             │
│   • AI Chat                  ◄────►    • Reasoning agent (Claude)        │
│   • Deal Command Center                • Deterministic math engine       │
│   • Approval Queue                     • Memory / knowledge base         │
│   • Daily Brief                        • Persona + voice module          │
│                                        • Training system                 │
│                                                                         │
│   INTEGRATIONS: ClickUp (live) · Apollo (import) · GHL/Gmail/Calendar   │
│                 (needs deployed server + OAuth)                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**Brain stack:** Python, FastAPI, ChromaDB (vector memory), Anthropic API.
**Cockpit stack:** React.
**Why split:** the Brain is the asset — it holds your judgment and your data. The Cockpit is replaceable glass in front of it. Keep the valuable part clean and isolated.

---

## 5. The Brain — components

### 5.1 Deterministic math engine
Pure functions, no AI. Computes:
- **DSCR** — floor 1.0, preferred 1.25+
- **Margin vs. ARV** — floor 25–30%
- **Flywheel revenue** — total revenue across all six touches for a given deal

The reasoning agent calls these and narrates the result. It is not permitted to produce a number any other way.

### 5.2 Memory / knowledge base (ChromaDB collections)
- `knowledge` — your rules, playbooks, pricing logic, Baker's evaluation checklist
- `voice` — examples of how you write and speak, for drafting in your voice
- `decisions` — your GO / NO-GO / CONDITIONAL calls with reasoning, recency-weighted
- `conversation_patterns` — full outreach exchanges: how you qualify, handle objections, close

### 5.3 Persona + voice module
Encodes your decision framework (including the Dan Martell 4-part framework and the flywheel logic) and your communication style. This is what makes an answer sound like you and not like generic AI.

### 5.4 Reasoning agent
Claude, given full context on every call: the relevant memory, the deal in question, the math engine's output. Produces the recommendation and the draft — always routed through the guardrails in §3.

### 5.5 Training system (the part you valued most)
- **`/train/deal-decision`** — you paste a deal (address, price, ARV, rehab, rent, notes) and your verdict + reasoning. It stores the example, runs the rules engine in parallel, and **flags divergence** when your gut call contradicts your own written rules. This surfacing of "you broke your own rule here — on purpose?" is a core feature, not a nice-to-have.
- **`/train/team-interaction`** — categories: coaching, accountability, praise, delegation, correction, firing.
- **`/train/conversation`** — full outreach threads.
- **`/decisions/history`** — every trained decision, newest first, filterable by type.
- **Bulk import** — CSV / JSON / JSONL / raw text, optional Claude auto-classification, plus an **Apollo CSV importer** that routes sent messages → voice, threaded exchanges → conversation patterns.

---

## 6. The Cockpit — modules

1. **AI Chat** — talk to the Brain with full pipeline context on every message. Live ClickUp access.
2. **Deal Command Center** — every deal with red / yellow / green **idle-day flagging** (deals going stale get loud) and a **flywheel revenue breakdown by vertical**.
3. **Approval Queue** — AI-drafted messages wait here. Approve / edit / deny. Nothing leaves without a decision (§3.3).
4. **Daily Brief** — pipeline by vertical, plus an AI-generated **top-three money moves** for the day.

**Seed deals for the demo build:** Titus (4-unit DSCR + modular ADU), Bobby (non-QM refi, 8 doors), Schill (QM purchase), Ridgeline (6-unit modular community).

---

## 7. Integrations

| Integration | Status | Notes |
|---|---|---|
| **ClickUp** | Live via MCP | Endpoint `https://mcp.clickup.com/mcp`, workspace `90141259054` |
| **Apollo** | Import built | CSV export → voice + conversation patterns |
| **GHL / Gmail / Calendar** | Not yet | Requires a deployed server (Next.js or equivalent), OAuth, and env vars. This is the main thing standing between a demo and a live system. |

---

## 8. Data model (core objects)

- **Deal** — address, purchase price, ARV, rehab estimate, rent, entity, vertical, status, idle-days, flywheel touches live
- **Decision** — deal ref, verdict (GO / NO-GO / CONDITIONAL), reasoning, timestamp, rules-engine result, divergence flag
- **TeamInteraction** — person, situation, your response, category
- **ConversationPattern** — contact, thread, extracted objection/close patterns
- **VoiceExample** — source text, tag
- **Rule** — the encoded playbook entries the engine and agent draw on

---

## 9. Encoded deal logic (the actual thresholds)

- Margin floor: **25–30% vs. ARV**
- DSCR: **floor 1.0, preferred 1.25+**
- Core markets: **Cleveland, Akron, Canton**
- Capital cost: **Joe 10% + 1 point**
- Goldfront lending: **12–14% + 1–2 points**
- DSCR takeout: **CB3 preferred**
- Flywheel: **hard money → construction → title → insurance → DSCR refi → property management**

---

## 10. Build sequence (for Cowork)

Don't build it as one blob. This order earns trust before it takes risk.

1. **Brain core** — math engine + memory + persona. Get the thing thinking correctly in your voice with correct numbers.
2. **Training loop** — the `/train/*` endpoints and bulk/Apollo import. Feed it your history so it's actually you, not a template.
3. **Validation (shadow mode)** — run it against ~20 historical decisions you already made. It has to match your calls before it's allowed to make them. Do not skip this.
4. **Cockpit** — Chat, Deal Command Center, Approval Queue, Daily Brief on top of a Brain that already works.
5. **Deploy + integrations** — stand up the server, wire GHL / Gmail / Calendar with OAuth, go live narrow (team Q&A and drafting) before deal structuring.

---

## 11. Open decisions for you

1. **Product name.** Kept as "Goldfront OS." If you'd rather it carry your name or the Stone Donut brand, say so and it propagates everywhere.
2. **Who else gets a seat.** Is the Cockpit just you, or do Emma/Aaron get scoped views? Affects auth from day one — cheaper to decide now.
3. **Where it lives.** Deployment target (and therefore how the OAuth integrations get built) is the one real infrastructure decision left. Worth settling before Cowork starts the deploy phase.

---

*End of spec. Hand this to Cowork as the founding document.*
