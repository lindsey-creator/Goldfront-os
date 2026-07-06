"""
Reasoning agent (master spec §5.4).

Claude, given full context on every call: the relevant memory, the deal in question,
and the deterministic engine's output. Produces the recommendation and any draft.

HARD RULES:
  §3.1 — narrates the numbers the engine produced; never computes them. Engine
         output is passed in; the model is told not to do arithmetic.
  §3.3 — drafts route to the Approval Queue; the agent never "sends".

Works with or without an API key:
  • ANTHROPIC_API_KEY set  → real reasoning via Claude, grounded in persona + memory + engine.
  • no key                 → an honest structured fallback: it still surfaces the engine's
                             numbers and the retrieved memory, and says plainly that live
                             narration needs a key. It never fabricates a number or a quote.
"""

from __future__ import annotations

import os

from brain.persona.persona import build_persona_prompt


def _retrieve(kb, message: str) -> dict:
    """Pull relevant memory for grounding. Safe if kb is None or empty."""
    out = {"voice": [], "decisions": [], "knowledge": [], "conversation_patterns": []}
    if kb is None:
        return out
    try:
        out["voice"] = kb.query("voice", message, n=3)
        out["knowledge"] = kb.query("knowledge", message, n=3)
        out["conversation_patterns"] = kb.query("conversation_patterns", message, n=2)
        out["decisions"] = kb.decisions_history(limit=3)
    except Exception:
        pass
    return out


def _fallback(message: str, engine: dict | None, memory: dict, wants_draft: bool) -> dict:
    """No API key: honest, grounded, no invented numbers or quotes."""
    bits = []
    if engine:
        m = engine.get("margin_vs_arv")
        d = engine.get("dscr")
        s = f"Engine says: rules verdict {engine.get('rules_verdict')}"
        if isinstance(m, (int, float)):
            s += f", margin {m:.1%}"
        if isinstance(d, (int, float)):
            s += f", DSCR {d:.2f}"
        bits.append(s + ".")
    known = sum(len(v) for v in memory.values())
    note = (
        "Live narration in your voice needs ANTHROPIC_API_KEY set on the Brain. "
        "Until then I return the engine's numbers and the most relevant things you've "
        "trained, without inventing anything."
    )
    return {
        "answer": " ".join(bits) if bits else "No deal numbers were provided to narrate.",
        "grounding": {
            "memory_hits": known,
            "voice": [r.get("text", "")[:160] for r in memory.get("voice", [])],
            "decisions": [r.get("metadata", {}).get("verdict") for r in memory.get("decisions", [])],
        },
        "engine": engine,
        "draft": None,
        "requires_approval": bool(wants_draft),
        "mode": "fallback",
        "note": note,
    }


def _claude(system: str, message: str, engine: dict | None, memory: dict, wants_draft: bool) -> dict | None:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic(api_key=key)
        model = os.getenv("GOLDFRONT_REASON_MODEL", "claude-sonnet-5")
        context = {"engine_output": engine, "retrieved_memory": memory, "wants_draft": wants_draft}
        user = (
            f"{message}\n\n---\nCONTEXT (engine numbers are authoritative; do not recompute):\n"
            f"{context}\n\n"
            "If you draft any outbound message, put it under a clear 'DRAFT:' heading — it goes "
            "to the Approval Queue, do not treat it as sent."
        )
        resp = client.messages.create(
            model=model,
            max_tokens=1200,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        draft = None
        if "DRAFT:" in text:
            draft = text.split("DRAFT:", 1)[1].strip()
        return {
            "answer": text,
            "engine": engine,
            "draft": draft,
            "requires_approval": bool(draft) or wants_draft,
            "mode": "claude",
        }
    except Exception as e:  # never crash the Brain on a model error
        return {"answer": None, "error": str(e), "engine": engine, "mode": "error"}


def reason(user_message: str, context: dict) -> dict:
    """
    context: {persona: str, engine: dict|None, memory: dict, wants_draft: bool}
    Returns narration + any draft (draft always requires approval).
    """
    system = context.get("persona") or build_persona_prompt()
    engine = context.get("engine")
    memory = context.get("memory", {})
    wants_draft = bool(context.get("wants_draft"))
    return _claude(system, user_message, engine, memory, wants_draft) or _fallback(
        user_message, engine, memory, wants_draft
    )


def answer(user_message: str, kb=None, engine: dict | None = None, wants_draft: bool = False) -> dict:
    """
    Convenience: retrieve memory, build the persona grounded on this question, and reason.
    `engine` is the deterministic output for a deal in question (or None for general Q&A).
    """
    memory = _retrieve(kb, user_message)
    system = build_persona_prompt(kb=kb, query=user_message)
    return reason(user_message, {"persona": system, "engine": engine, "memory": memory, "wants_draft": wants_draft})
