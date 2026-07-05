"""
Training service (master spec §5.5).

All training logic lives here so the FastAPI endpoints AND the bulk/Apollo/ClickUp/
Fieldy importers share one implementation. Endpoints are thin wrappers; importers
call these methods directly.

Nothing here computes deal money — deal-decision training routes the numbers
through the deterministic engine (§3.1) and only stores/compares the result.
"""

from __future__ import annotations

import time

from brain.engine.deal_math import (
    DealInputs,
    evaluate_deal,
    margin_vs_arv,
    rules_engine_verdict,
)
from brain.memory.knowledge_base import KnowledgeBase
from brain.training.classifier import classify
from brain.training.schemas import (
    TEAM_CATEGORIES,
    ConversationPatternIn,
    DealDecisionIn,
    TeamInteractionIn,
    VoiceExampleIn,
    normalize_verdict,
)


def _evaluate_or_partial(inputs: DealInputs) -> dict:
    """
    Full engine evaluation when we have rent + debt service. When those are
    missing (e.g. a flip, not a rental), fall back to a margin-only view:
    without coverage data the rules can never bless a clean GO — the best a
    margin-only deal earns is CONDITIONAL, or NO-GO if the margin is thin.
    The trustworthy engine itself is never weakened; this is a training guard.
    """
    try:
        return evaluate_deal(inputs)
    except ValueError:
        margin = margin_vs_arv(
            inputs.purchase_price, inputs.rehab_estimate, inputs.arv, inputs.other_costs
        )
        # coverage unknown -> treat as failing the "preferred" bar so GO is impossible
        verdict = rules_engine_verdict(margin, coverage=0.0)
        if verdict == "NO-GO" and margin >= 0.25:
            # margin is fine; the only reason we'd say NO-GO is missing DSCR data
            verdict = "CONDITIONAL"
        return {
            "margin_vs_arv": round(margin, 4),
            "margin_pass": margin >= 0.25,
            "dscr": None,
            "dscr_pass": None,
            "flywheel": None,
            "rules_verdict": verdict,
            "partial": True,
            "note": "DSCR not computed — no rent/debt-service provided.",
        }


class TrainingService:
    def __init__(self, kb: KnowledgeBase | None = None):
        self.kb = kb or KnowledgeBase()

    # -- voice --------------------------------------------------------------
    def train_voice(self, ex: VoiceExampleIn) -> dict:
        recipient, context, method = ex.recipient, ex.context, "provided"
        if not recipient or not context:
            guess = classify(ex.text)
            recipient = recipient or guess["recipient"]
            context = context or guess["context"]
            method = guess["method"]
        meta = {"source": ex.source or "manual", "classify_method": method}
        rid = self.kb.add_voice(ex.text, recipient, context, meta)
        return {"id": rid, "recipient": recipient, "context": context, "classify_method": method}

    # -- deal decisions -----------------------------------------------------
    def train_deal_decision(self, d: DealDecisionIn) -> dict:
        verdict = normalize_verdict(d.verdict)
        inputs = DealInputs(
            purchase_price=d.purchase_price,
            rehab_estimate=d.rehab_estimate,
            arv=d.arv,
            monthly_rent=d.monthly_rent,
            monthly_debt_service=d.monthly_debt_service,
            other_costs=d.other_costs,
        )
        engine = _evaluate_or_partial(inputs)  # runs the engine in parallel (§5.5)
        rules_verdict = engine["rules_verdict"]
        diverged = rules_verdict != verdict
        text = (
            f"DEAL: {d.address}\n"
            f"Purchase ${d.purchase_price:,.0f} | ARV ${d.arv:,.0f} | "
            f"Rehab ${d.rehab_estimate:,.0f} | Rent ${d.monthly_rent:,.0f}/mo\n"
            f"VERDICT: {verdict}\n"
            f"WHY: {d.reasoning}\n"
            f"NOTES: {d.notes}"
        )
        metadata = {
            "address": d.address,
            "verdict": verdict,
            "rules_verdict": rules_verdict,
            "diverged": diverged,
            "purchase_price": d.purchase_price,
            "arv": d.arv,
            "reasoning": d.reasoning,
            "_ts": time.time(),
        }
        rid = self.kb.add_decision(text, metadata)
        return {
            "id": rid,
            "verdict": verdict,
            "rules_verdict": rules_verdict,
            "diverged": diverged,
            "engine": engine,
            "divergence_note": (
                f"Heads up — your call ({verdict}) contradicts your own rules "
                f"({rules_verdict}). On purpose?"
                if diverged
                else "Your call matches your rules."
            ),
        }

    def decisions_history(self, verdict: str | None = None, limit: int | None = None) -> list[dict]:
        v = normalize_verdict(verdict) if verdict else None
        return self.kb.decisions_history(verdict=v, limit=limit)

    # -- team interactions --------------------------------------------------
    def train_team_interaction(self, ti: TeamInteractionIn) -> dict:
        category, method = ti.category, "provided"
        if not category:
            guess = classify(f"{ti.situation}\n{ti.response}")
            category = guess["context"]
            method = guess["method"]
        if category not in TEAM_CATEGORIES:
            category = "coaching"  # safe default within the allowed set
        text = f"PERSON: {ti.person}\nSITUATION: {ti.situation}\nMY RESPONSE: {ti.response}"
        rid = self.kb.add_team_interaction(text, category, ti.person, {"classify_method": method})
        return {"id": rid, "person": ti.person, "category": category, "classify_method": method}

    # -- conversations ------------------------------------------------------
    def train_conversation(self, c: ConversationPatternIn) -> dict:
        meta = {
            "contact": c.contact,
            "company": c.company,
            "title": c.title,
            "email": c.email,
            "source": c.source or "manual",
        }
        rid = self.kb.add_conversation(c.thread, meta)
        return {"id": rid, "contact": c.contact, "company": c.company}

    # -- counts (handy for import summaries) --------------------------------
    def counts(self) -> dict:
        return {
            "voice": self.kb.count("voice"),
            "decisions": self.kb.count("decisions"),
            "conversation_patterns": self.kb.count("conversation_patterns"),
            "knowledge": self.kb.count("knowledge"),
        }
