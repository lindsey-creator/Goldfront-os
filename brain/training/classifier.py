"""
Auto-classification for untagged messages (master spec §5.5).

When you dump raw text with no metadata, we still need two labels per message:
  • recipient : team | client | partner | recruit | unknown
  • context   : closing | feedback | follow_up | challenge | praise | coaching |
                accountability | delegation | correction | firing | qualifying |
                objection_handling | general

Two paths:
  • Claude path — used when ANTHROPIC_API_KEY is set. Accurate, handles nuance.
  • Heuristic path — keyword rules. No key, no network needed. Always available,
                     which is why the importers never block on classification.

`classify()` picks the Claude path when possible and silently falls back.
"""

from __future__ import annotations

import json
import os

RECIPIENTS = ("team", "client", "partner", "recruit", "unknown")
CONTEXTS = (
    "closing",
    "feedback",
    "follow_up",
    "challenge",
    "praise",
    "coaching",
    "accountability",
    "delegation",
    "correction",
    "firing",
    "qualifying",
    "objection_handling",
    "general",
)

# Names the Brain knows (master spec §2) — a strong signal the recipient is team/partner.
TEAM_NAMES = {"emma", "aaron", "gen", "ryan", "baker", "bobby", "brett", "tracy"}
PARTNER_NAMES = {"ken", "joe", "cb3"}

_CONTEXT_KEYWORDS = {
    "closing": ["let's get this signed", "wire the funds", "send the wire", "ready to close", "send the docs", "ready to move", "lock it in", "term sheet", "let's close"],
    "objection_handling": ["i understand your concern", "that's fair, but", "what's holding you", "hesitat", "too expensive", "too high", "the reason it's worth"],
    "qualifying": ["what's your budget", "how many doors", "what's your timeline", "are you looking to", "tell me about the property", "what's the arv", "what's the rehab"],
    "follow_up": ["following up", "just checking in", "circling back", "wanted to check", "any update", "touch base"],
    "praise": ["great job", "proud of you", "crushed it", "well done", "nailed it", "awesome work", "killed it"],
    "correction": ["that's not how we", "we don't do that", "need you to fix", "this was wrong", "redo this", "shouldn't have"],
    "accountability": ["you said you'd", "dropped the ball", "where is the", "you committed", "this was due", "own it", "missed the deadline", "you didn't follow through"],
    "coaching": ["here's how", "next time try", "the way to think about", "what i'd do", "let me walk you", "lesson here"],
    "delegation": ["can you take", "i need you to", "please handle", "run point on", "own this", "you've got this one"],
    "firing": ["this isn't working out", "we're going to part ways", "have to let you go", "your last day"],
    "challenge": ["why did you", "push back", "i disagree", "convince me", "not good enough", "explain your thinking"],
    "feedback": ["one thing i'd", "i'd suggest", "my read is", "here's my feedback", "constructive"],
}

# On a score tie, management/correction signals beat generic sales signals.
# Ordered most-specific-and-important first.
_CONTEXT_PRIORITY = [
    "firing",
    "correction",
    "accountability",
    "coaching",
    "delegation",
    "challenge",
    "objection_handling",
    "qualifying",
    "closing",
    "praise",
    "feedback",
    "follow_up",
    "general",
]


def _heuristic(text: str) -> dict:
    t = (text or "").lower()

    recipient = "unknown"
    if any(n in t for n in PARTNER_NAMES):
        recipient = "partner"
    elif any(n in t for n in TEAM_NAMES):
        recipient = "team"
    elif any(w in t for w in ["thanks for reaching out", "your loan", "your property", "pre-approv", "your application", "congratulations on"]):
        recipient = "client"
    elif any(w in t for w in ["join our team", "role at", "opportunity to work", "hiring", "your resume"]):
        recipient = "recruit"

    scores = {}
    for ctx, kws in _CONTEXT_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in t)
        if hits:
            scores[ctx] = hits

    if not scores:
        context = "general"
    else:
        best = max(scores.values())
        tied = [c for c, s in scores.items() if s == best]
        # break ties by priority order
        context = min(tied, key=lambda c: _CONTEXT_PRIORITY.index(c))

    return {"recipient": recipient, "context": context, "method": "heuristic"}


def _claude(text: str) -> dict | None:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic(api_key=key)
        model = os.getenv("GOLDFRONT_CLASSIFY_MODEL", "claude-sonnet-5")
        prompt = (
            "Classify this business message. Return ONLY JSON: "
            '{"recipient": one of ' + json.dumps(list(RECIPIENTS)) + ", "
            '"context": one of ' + json.dumps(list(CONTEXTS)) + "}.\n\n"
            f"Message:\n{text}"
        )
        resp = client.messages.create(
            model=model,
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
        data = json.loads(raw)
        recipient = data.get("recipient", "unknown")
        context = data.get("context", "general")
        return {
            "recipient": recipient if recipient in RECIPIENTS else "unknown",
            "context": context if context in CONTEXTS else "general",
            "method": "claude",
        }
    except Exception:
        return None  # never let classification block an import


def classify(text: str) -> dict:
    """Return {recipient, context, method}. Claude when available, else heuristic."""
    return _claude(text) or _heuristic(text)


def classify_batch(texts: list[str]) -> list[dict]:
    return [classify(t) for t in texts]
