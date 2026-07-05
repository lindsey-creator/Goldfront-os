"""
Training system (master spec §5.5) — the part that makes the Brain YOU.

Endpoints (to be mounted on the FastAPI app):
    POST /train/deal-decision   store a deal + your GO/NO-GO/CONDITIONAL + why.
                                Runs the rules engine in parallel and FLAGS
                                DIVERGENCE when your gut contradicts your rules.
    POST /train/team-interaction  categories: coaching, accountability, praise,
                                  delegation, correction, firing.
    POST /train/conversation    full outreach threads.
    GET  /decisions/history     all trained decisions, newest first, filterable.

Bulk import (scripts, not endpoints): CSV / JSON / JSONL / raw text, optional
Claude auto-classification, plus an Apollo CSV importer routing sent messages ->
voice and threaded exchanges -> conversation_patterns.

STUB: build in Cowork. The divergence check below shows the intended shape.
"""

from brain.engine.deal_math import DealInputs, evaluate_deal

TEAM_CATEGORIES = (
    "coaching",
    "accountability",
    "praise",
    "delegation",
    "correction",
    "firing",
)


def check_divergence(inputs: DealInputs, human_verdict: str) -> dict:
    """
    Compare the human's gut call to the mechanical rules verdict.
    Divergence isn't an error — it's signal worth surfacing (§5.5).
    """
    engine = evaluate_deal(inputs)
    diverged = engine["rules_verdict"] != human_verdict.upper()
    return {
        "human_verdict": human_verdict.upper(),
        "rules_verdict": engine["rules_verdict"],
        "diverged": diverged,
        "engine": engine,
    }
