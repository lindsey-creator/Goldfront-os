"""
Request/record shapes for the training system (master spec §5.5, §8).

Pydantic models so the FastAPI endpoints validate input, and the importers can
build the same objects programmatically.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from brain.training.classifier import CONTEXTS, RECIPIENTS

TEAM_CATEGORIES = (
    "coaching",
    "accountability",
    "praise",
    "delegation",
    "correction",
    "firing",
)


class VoiceExampleIn(BaseModel):
    text: str
    recipient: str | None = None  # team|client|partner|recruit|unknown (auto if None)
    context: str | None = None    # auto-classified if None
    source: str | None = None     # e.g. "apollo", "bulk", "manual", "fieldy"


class DealDecisionIn(BaseModel):
    address: str
    purchase_price: float
    arv: float
    rehab_estimate: float = 0.0
    monthly_rent: float = 0.0
    monthly_debt_service: float = 0.0
    other_costs: float = 0.0
    verdict: str = Field(..., description="GO | NO-GO | CONDITIONAL")
    reasoning: str = ""
    notes: str = ""


class TeamInteractionIn(BaseModel):
    person: str
    situation: str
    response: str
    category: str | None = None  # one of TEAM_CATEGORIES (auto-classified if None)


class ConversationPatternIn(BaseModel):
    contact: str = ""
    company: str = ""
    title: str = ""
    email: str = ""
    thread: str  # the full exchange, formatted
    source: str | None = None


def normalize_verdict(v: str) -> str:
    """Map loose input to the canonical GO / NO-GO / CONDITIONAL."""
    s = (v or "").strip().upper().replace("_", "-").replace(" ", "-")
    if s in ("GO", "YES", "APPROVE", "APPROVED"):
        return "GO"
    if s in ("NO-GO", "NO", "NOGO", "PASS", "DECLINE", "DENY", "DENIED"):
        return "NO-GO"
    if s in ("CONDITIONAL", "MAYBE", "COND", "IF"):
        return "CONDITIONAL"
    return s or "UNKNOWN"
