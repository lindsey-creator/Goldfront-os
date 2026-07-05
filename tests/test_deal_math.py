"""
Tests for the deterministic engine. If these don't pass, nothing downstream
can be trusted — the whole point of the engine is that the math is correct.
"""

import pytest

from brain.engine.deal_math import (
    DealInputs,
    margin_vs_arv,
    dscr,
    flywheel_revenue,
    rules_engine_verdict,
    evaluate_deal,
)


def test_margin_basic():
    # ARV 200k, all-in 140k -> 30% margin
    assert margin_vs_arv(120_000, 20_000, 200_000) == pytest.approx(0.30)


def test_margin_with_other_costs():
    assert margin_vs_arv(120_000, 20_000, 200_000, other_costs=10_000) == pytest.approx(0.25)


def test_margin_zero_arv_raises():
    with pytest.raises(ValueError):
        margin_vs_arv(100_000, 0, 0)


def test_dscr_basic():
    assert dscr(1_500, 1_200) == pytest.approx(1.25)


def test_dscr_zero_debt_raises():
    with pytest.raises(ValueError):
        dscr(1_500, 0)


def test_flywheel_totals_and_live_touches():
    result = flywheel_revenue(
        {"hard_money": 5_000, "title": 1_200, "construction": 0}
    )
    assert result["total_revenue"] == 6_200
    assert result["live_touches"] == ["hard_money", "title"]  # zero-value dropped
    assert result["touches_live_count"] == 2
    assert result["touches_possible"] == 6


def test_flywheel_rejects_unknown_touch():
    with pytest.raises(ValueError):
        flywheel_revenue({"not_a_real_touch": 100})


def test_verdict_go():
    assert rules_engine_verdict(margin=0.32, coverage=1.30) == "GO"


def test_verdict_nogo_on_margin():
    assert rules_engine_verdict(margin=0.20, coverage=1.50) == "NO-GO"


def test_verdict_nogo_on_dscr():
    assert rules_engine_verdict(margin=0.40, coverage=0.90) == "NO-GO"


def test_verdict_conditional():
    assert rules_engine_verdict(margin=0.27, coverage=1.10) == "CONDITIONAL"


def test_evaluate_deal_end_to_end():
    inputs = DealInputs(
        purchase_price=120_000,
        rehab_estimate=20_000,
        arv=200_000,
        monthly_rent=1_500,
        monthly_debt_service=1_200,
        flywheel_revenue_by_touch={"hard_money": 5_000, "dscr_refi": 3_000},
    )
    out = evaluate_deal(inputs)
    assert out["margin_vs_arv"] == pytest.approx(0.30)
    assert out["dscr"] == pytest.approx(1.25)
    assert out["margin_pass"] is True
    assert out["dscr_preferred"] is True
    assert out["flywheel"]["total_revenue"] == 8_000
    assert out["rules_verdict"] == "GO"
