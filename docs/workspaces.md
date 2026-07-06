# Workspaces — separate brains, one codebase

Lindsey, Ryan Arth, and Ryan Baker are partners in Goldfront and each gets their
**own private brain**. Lindsey's brain must stay separate from theirs. This is how
that works — and why it's one repo, not three.

## Order & naming (Lindsey's directive)
- **Conrad Command Center = Lindsey's own private brain** (workspace `lindsey`).
  **Build hers first, get it right** — before anyone else's.
- **Goldfront = the base** the other owners (Ryan Arth, Ryan Baker) and the wider
  team run from: a per-owner private brain each, plus the `goldfront-shared`
  workspace for partnership-common knowledge. Rolled out *after* Lindsey's works.
- Same codebase powers both. Conrad Command Center is simply the first, private
  instance; Goldfront is the same thing templated for everyone else.

## The model
- **One codebase** (`goldfront-os`). Three code repos would mean maintaining the
  same engine three times — the opposite of "build once." So the code is shared;
  the *data* is not.
- **A workspace per person.** Each owner's memory lives in its own physical store,
  namespaced by workspace id: `lindsey`, `ryan-arth`, `ryan-baker`. Two brains
  under the same base directory are fully isolated — one cannot read the other's
  voice, decisions, conversations, or personal data. (Proven in
  `tests/test_workspaces.py`.)
- **A shared workspace** (`goldfront-shared`) for what the partnership deliberately
  holds in common — Goldfront deal rules, the pipeline, shared playbooks. Opt-in,
  explicit; nobody's private brain flows into it automatically.

## How each person runs their brain
Set the owner and (optionally) where memory lives:

```bash
# Lindsey's brain
GOLDFRONT_OWNER=lindsey uvicorn brain.main:app --reload

# Ryan Arth's brain (separate data, same code)
GOLDFRONT_OWNER=ryan-arth uvicorn brain.main:app

# Ryan Baker's brain
GOLDFRONT_OWNER=ryan-baker uvicorn brain.main:app
```

`GOLDFRONT_MEMORY_PATH` sets the base directory; each owner gets a subfolder under
it. In production the cleanest setup is a **separate deployment per person** (own
server or container, own private storage) — strongest isolation, and Lindsey's data
never sits next to a partner's. The shared workspace can be its own small service
both instances read.

## In code
```python
from brain.memory.knowledge_base import KnowledgeBase

mine   = KnowledgeBase()                    # defaults to GOLDFRONT_OWNER
arth   = KnowledgeBase(workspace="ryan-arth")
shared = KnowledgeBase.shared()             # goldfront-shared
```

## What stays private vs shared (recommended)
- **Private (per owner):** voice, decisions, conversation_patterns, personal
  council data (health, calendar, wellbeing). This is *you* — never shared.
- **Shared (opt-in):** Goldfront deal rules, pipeline status, team playbooks —
  the stuff partners genuinely run together.

## Command Center
Each partner opens their own Command Center pointed at their own brain. A future
"Goldfront team view" can read the shared workspace for joint pipeline — with
scoped access, so a partner sees shared deal data without seeing anyone's private
brain. Decide per-seat access when you add partners (master-spec §11 #2).
