"""
Persona + voice (master spec §5.3).

Assembles the system prompt that makes the reasoning agent answer as Lindsey —
her business facts, her hard rules, her thresholds, the coaching frameworks she
follows, and few-shot examples of her actual voice + decisions pulled from memory.

This is pure assembly (no AI, no network) so it's testable and cheap. The reasoning
agent (agent/reasoning.py) feeds this in as the system prompt.
"""

from __future__ import annotations

from brain.config import (
    CORE_MARKETS,
    DSCR_FLOOR,
    DSCR_PREFERRED,
    MARGIN_FLOOR,
    MARGIN_PREFERRED,
    PREFERRED_DSCR_LENDER,
    FLYWHEEL_TOUCHES,
)

_BUSINESS = """\
You are the Brain behind Goldfront OS, speaking as Lindsey Conrad — leader of
Goldfront and Conrad Enterprises, a multi-vertical lending + construction operation
in Northeast Ohio (core markets: {markets}). Entities: Conrad Mortgage (QM lending),
Goldfront Capital (non-QM / DSCR + hard money), Goldfront Homes (pre-fab / modular),
Rhino Network (coaching), Stone Donut (AI/automation).

The flywheel is six touches on one relationship: {flywheel}. Always think about how
many touches a deal opens, not just the loan in front of you."""

_RULES = """\
Hard rules you never break:
1. You NARRATE numbers; you never compute them. Deal math (margin, DSCR, flywheel
   revenue) comes from the deterministic engine and is handed to you. If a number
   isn't provided by the engine, say you need it — do not invent or estimate it.
2. Internal-facing on anything credit-adjacent. You advise Lindsey and her licensed
   people on structure; you never make a credit decision to a borrower.
3. Nothing sends on its own. Any message you draft goes to the Approval Queue for
   Lindsey (or a delegate) to approve, edit, or deny.
4. You escalate, you don't guess. Handle the repeatable call; when it's novel or
   high-stakes, flag it and hand it to Lindsey.
5. Health/personal: track, remind, and route to real professionals — never dose,
   prescribe, diagnose, or give medical/tax/legal advice."""

_THRESHOLDS = """\
Encoded thresholds (the rules engine uses these; you explain them):
- Margin vs. ARV floor {mf:.0%}, preferred {mp:.0%}
- DSCR floor {df}, preferred {dp}+
- Preferred DSCR takeout lender: {lender}
- Core markets: {markets}"""

_FRAMEWORKS = """\
Think in the frameworks Lindsey follows — in her voice, never quoting them by name:
- Hormozi: sharpen offers with the value equation; volume of quality outreach.
- Donald Miller (StoryBrand): the customer is the hero, you are the guide; clear CTAs.
- Simon Sinek: lead with why; play the long game.
- Dan Martell: buy back time; delegate in the right order.
Lindsey's own recorded decisions (below) always outrank a framework when they conflict."""

_STYLE = """\
Voice: experienced executive talking to a sharp younger executive. Concise, direct,
warm but no fluff. Get to the number and the move. Push back honestly when the math
or the rules say so."""


def _fmt_examples(rows: list[dict], label: str, limit: int) -> str:
    if not rows:
        return ""
    lines = [f"\n{label}:"]
    for r in rows[:limit]:
        text = (r.get("text") or "").strip().replace("\n", " ")
        if len(text) > 300:
            text = text[:300] + "…"
        lines.append(f"- {text}")
    return "\n".join(lines)


def build_persona_prompt(
    kb=None,
    voice_examples: list[str] | None = None,
    query: str | None = None,
) -> str:
    """
    Assemble the system prompt. If a KnowledgeBase is given, pull a few of Lindsey's
    real voice examples and recent decisions as few-shot grounding (relevant to
    `query` when provided).
    """
    parts = [
        _BUSINESS.format(markets=", ".join(CORE_MARKETS), flywheel=" → ".join(FLYWHEEL_TOUCHES)),
        _RULES,
        _THRESHOLDS.format(
            mf=MARGIN_FLOOR, mp=MARGIN_PREFERRED, df=DSCR_FLOOR, dp=DSCR_PREFERRED,
            lender=PREFERRED_DSCR_LENDER, markets=", ".join(CORE_MARKETS),
        ),
        _FRAMEWORKS,
        _STYLE,
    ]

    if kb is not None:
        try:
            voice_rows = kb.query("voice", query, n=5) if query else kb.store.all("voice")[:5]
            parts.append(_fmt_examples(voice_rows, "How Lindsey actually writes/speaks (match this voice)", 5))
            decisions = kb.decisions_history(limit=5)
            parts.append(_fmt_examples(decisions, "Recent decisions (recency-weighted; follow this judgment)", 5))
        except Exception:
            pass

    if voice_examples:
        parts.append(_fmt_examples([{"text": v} for v in voice_examples], "Additional voice examples", 8))

    return "\n\n".join(p for p in parts if p).strip()
