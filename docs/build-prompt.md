# Build prompt — Command Center (Cursor / Manus / Fable)

Paste the block below into **whichever build tool you're using — Cursor, Manus, or
Fable.** It's written to be tool-agnostic. Use it once the Brain has been trained
and validated (master-spec §10, steps 2–3). Everything below the line is the prompt.

---

You are building the **Conrad Command Center** — the interface for Goldfront OS,
the private operating system that runs Lindsey Conrad's lending + construction
operation (Goldfront + Conrad Enterprises, 8 business units) AND supports her
personally as an elite operator.

**Read these first as the source of truth, in order:**
1. `docs/master-spec.md` — architecture, hard principles, data model
2. `docs/executive-council.md` — the vision: a board of executives (business + personal seats)
3. `docs/command-center-experience.md` — the experience/design spec + modules
4. `docs/coaching-frameworks.md` — the voices to bake into the Brain (Hormozi, Miller, Sinek, Martell)
5. `README.md` + `docs/training-and-import.md` — what's already built

**Match and elevate the existing dashboard.** Lindsey already runs
`command.theconradteam.com` (Manus, "SYSTEM v4.1", ClickUp + GCal + GHL + Gmail +
Weather, mobile-locked, 15-min refresh). Rebuild it to feel like **something
nobody has seen** — calm, elite, uncluttered, so clear it's hard to mess up. When
she opens it she should feel **"we got this."**

**Non-negotiables (master-spec §3):**
- The deterministic engine (`brain/engine/deal_math.py`) computes every number; the
  UI and agents NARRATE numbers, never calculate them.
- Nothing sends without a human gate (Approval Queue).
- Escalate the novel 20%; don't guess. Credit-adjacent = internal-facing only.
- **Wellbeing guardrail**: health/performance modules track, display, remind, and
  route to real professionals — they never dose, prescribe, diagnose, or give
  medical/tax/investment advice.

**Mobile-first / travel:** she runs this from a Cybertruck (autodrive) on Starlink
Mini. It must be excellent and fast on a phone/tablet and degrade gracefully on a
weak connection. **Build once, build durable — she does not want to rebuild this.**

**Modules to build (one screen):**
Business — Empire Blind Spots · Today's Watch List (CRITICAL) · Money in Motion
(with the Top-3 money moves) · GoHighLevel CRM (leads/missed calls/texts/pipeline)
· Meta Ads (spend/leads/CPL) · Team Pulse (overdue + who's behind) · Schedule ·
Week Ahead · Weather.
Personal — Health & performance (Apple Health + Whoop, supplement schedule,
peptide protocol, diet) · Calendar protection · Wellbeing check-in. All personal
modules obey the wellbeing guardrail.

**Three capabilities on top of the old dashboard:**
1. **Daily Fieldy brief** — she wears Fieldy all day; each morning produce a brief
   of her entire day: decisions, commitments she made, promises others made to her,
   follow-ups owed, and items that should become tasks or watch-list entries.
2. **Accountability radar** — cross-reference what people said they'd do (Fieldy,
   ClickUp, recorded GHL calls, email) against what actually moved; surface the
   person, the gap, and a suggested move. This is "watch for holes / people not
   doing the right thing."
3. **Task-from-anywhere** — issue tasks to the team into ClickUp by voice or text
   from the road; the Brain routes them to the right person with context; approvals
   happen from her phone.

**End-state to design toward:** whole team on ClickUp, everyone on GHL with all
calls recorded, so Lindsey sees everything daily and issues tasks while traveling —
growing the business while enjoying her life.

**Stack & order:** React front end talking to the existing FastAPI Brain; reuse
`/evaluate-deal`, `/train/*`, `/decisions/history` and add the read endpoints the
Command Center needs. Keep the Brain as the source of truth and the UI as
replaceable glass. Build the shell + a couple of live modules first (they work on
today's Brain), then the money moves + accountability radar, then the personal
modules. **Never fake data** — wire to the Brain and to live connectors; where a
source isn't connected, show a clean "connect this source" state.
