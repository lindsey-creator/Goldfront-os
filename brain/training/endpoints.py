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


# ---------------------------------------------------------------------------
# FastAPI router — mounted by brain.main
# ---------------------------------------------------------------------------
# TrainingService is imported lazily inside the factory to avoid a circular
# import (service.py imports check_divergence from this module).
from functools import lru_cache  # noqa: E402

from fastapi import APIRouter, Depends  # noqa: E402

from brain.training.schemas import (  # noqa: E402
    ConversationPatternIn,
    DealDecisionIn,
    TeamInteractionIn,
    VoiceExampleIn,
)

router = APIRouter(tags=["training"])


@lru_cache(maxsize=1)
def get_service():
    from brain.training.service import TrainingService

    return TrainingService()


@router.post("/train/voice")
def train_voice(ex: VoiceExampleIn, svc=Depends(get_service)):
    return svc.train_voice(ex)


@router.post("/train/deal-decision")
def train_deal_decision(d: DealDecisionIn, svc=Depends(get_service)):
    return svc.train_deal_decision(d)


@router.post("/train/team-interaction")
def train_team_interaction(ti: TeamInteractionIn, svc=Depends(get_service)):
    return svc.train_team_interaction(ti)


@router.post("/train/conversation")
def train_conversation(c: ConversationPatternIn, svc=Depends(get_service)):
    return svc.train_conversation(c)


@router.get("/decisions/history")
def decisions_history(verdict: str | None = None, limit: int | None = None, svc=Depends(get_service)):
    return {"decisions": svc.decisions_history(verdict=verdict, limit=limit)}


@router.get("/train/counts")
def counts(svc=Depends(get_service)):
    return svc.counts()
