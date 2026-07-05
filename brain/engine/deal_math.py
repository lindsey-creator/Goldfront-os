"""
Deterministic deal-math engine.

HARD RULE (master spec §3.1): the Brain narrates, it never computes. All money
math lives here, in pure functions. The language model is not permitted to
produce any of these numbers by any other route. This module has no AI in it
and no side effects — same inputs, same outputs, every time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

from brain.config import (
    MARGIN_FLOOR,
    MARGIN_PREFERRED,
    DSCR_FLOOR,
    DSCR_PREFERRED,
    FLYWHEEL_TOUCHES,
)


@dataclass
class DealInputs:
    """Everything the engine needs. Nothing is inferred — you give it real numbers."""
    purchase_price: float
    rehab_estimate: float
    arv: float
    monthly_rent: float
    monthly_debt_service: float
    other_costs: float = 0.0
    # revenue expected from each live flywheel touch, keyed by touch name
    flywheel_revenue_by_touch: Dict[str, float] = field(default_factory=dict)


def margin_vs_arv(
    purchase_price: float,
    rehab_estimate: float,
    arv: float,
    other_costs: float = 0.0,
) -> float:
    """
    Margin as a fraction of ARV: (ARV - all-in cost) / ARV.
    Floor is 25% (config.MARGIN_FLOOR), 30%+ preferred.
    """
    if arv <= 0:
        raise ValueError("ARV must be positive to compute margin.")
    all_in = purchase_price + rehab_estimate + other_costs
    return (arv - all_in) / arv


def dscr(monthly_rent: float, monthly_debt_service: float) -> float:
    """
    Debt service coverage ratio: rent / debt payment.
    Floor is 1.0 (config.DSCR_FLOOR), 1.25+ preferred.
    """
    if monthly_debt_service <= 0:
        raise ValueError("Monthly debt service must be positive to compute DSCR.")
    return monthly_rent / monthly_debt_service


def flywheel_revenue(revenue_by_touch: Dict[str, float]) -> dict:
    """
    Total revenue across the six-touch flywheel, plus which touches are live.
    Unknown touch names are rejected so a typo can't silently drop revenue.
    """
    for touch in revenue_by_touch:
        if touch not in FLYWHEEL_TOUCHES:
            raise ValueError(
                f"Unknown flywheel touch '{touch}'. Valid: {FLYWHEEL_TOUCHES}"
            )
    live = {t: amt for t, amt in revenue_by_touch.items() if amt > 0}
    return {
        "total_revenue": round(sum(live.values()), 2),
        "live_touches": sorted(live.keys()),
        "touches_live_count": len(live),
        "touches_possible": len(FLYWHEEL_TOUCHES),
    }


def rules_engine_verdict(margin: float, coverage: float) -> str:
    """
    The MECHANICAL verdict from your written rules — not a human judgment.

    This exists so the training system can flag divergence (spec §5.5): when
    your gut call (GO) contradicts what the rules say (NO-GO), the system
    surfaces it. This function is the "what the rules say" half of that.

        GO          margin >= 30% AND DSCR >= 1.25
        NO-GO       margin < 25%  OR  DSCR < 1.0
        CONDITIONAL everything in between
    """
    if margin >= MARGIN_PREFERRED and coverage >= DSCR_PREFERRED:
        return "GO"
    if margin < MARGIN_FLOOR or coverage < DSCR_FLOOR:
        return "NO-GO"
    return "CONDITIONAL"


def evaluate_deal(inputs: DealInputs) -> dict:
    """
    Run the full mechanical evaluation of a deal. Returns numbers + the rules
    verdict. Human verdict and reasoning are recorded separately by the
    training system; comparing the two is how divergence gets flagged.
    """
    margin = margin_vs_arv(
        inputs.purchase_price, inputs.rehab_estimate, inputs.arv, inputs.other_costs
    )
    coverage = dscr(inputs.monthly_rent, inputs.monthly_debt_service)
    flywheel = flywheel_revenue(inputs.flywheel_revenue_by_touch)

    return {
        "margin_vs_arv": round(margin, 4),
        "margin_pass": margin >= MARGIN_FLOOR,
        "margin_preferred": margin >= MARGIN_PREFERRED,
        "dscr": round(coverage, 4),
        "dscr_pass": coverage >= DSCR_FLOOR,
        "dscr_preferred": coverage >= DSCR_PREFERRED,
        "flywheel": flywheel,
        "rules_verdict": rules_engine_verdict(margin, coverage),
    }
