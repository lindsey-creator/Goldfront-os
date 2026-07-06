"""Persona assembly + reasoning agent (fallback path — no API key in tests)."""

from brain.agent import reasoning
from brain.persona.persona import build_persona_prompt
from brain.training.schemas import DealDecisionIn, VoiceExampleIn


def test_persona_contains_business_rules_and_thresholds():
    p = build_persona_prompt()
    assert "Lindsey Conrad" in p
    assert "NARRATE numbers" in p          # the hard rule is present
    assert "25%" in p and "DSCR" in p       # thresholds surfaced
    assert "CB3" in p                       # preferred lender
    assert "hero" in p                      # StoryBrand framework baked in


def test_persona_pulls_voice_and_decisions_from_memory(svc, kb):
    svc.train_voice(VoiceExampleIn(text="Aaron, hold margin at 30% on Titus.", recipient="team", context="coaching"))
    svc.train_deal_decision(DealDecisionIn(
        address="1 Real St", purchase_price=80000, arv=200000, rehab_estimate=30000,
        monthly_rent=2000, monthly_debt_service=1200, verdict="GO", reasoning="clean"))
    p = build_persona_prompt(kb=kb, query="Titus margin")
    assert "Titus" in p                     # her real voice example made it in
    assert "Recent decisions" in p


def test_reason_fallback_narrates_engine_numbers_no_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    engine = {"rules_verdict": "GO", "margin_vs_arv": 0.35, "dscr": 1.67}
    out = reasoning.reason("Should I do this deal?", {"engine": engine, "memory": {}})
    assert out["mode"] == "fallback"
    assert "GO" in out["answer"]
    assert "35" in out["answer"] or "35.0%" in out["answer"]   # narrates engine margin
    assert out["draft"] is None


def test_reason_never_invents_when_no_engine(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = reasoning.reason("What do you think?", {"engine": None, "memory": {}})
    assert "No deal numbers" in out["answer"]  # honest, doesn't fabricate a number


def test_answer_wants_draft_requires_approval(monkeypatch, kb):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    out = reasoning.answer("Draft a follow-up to the borrower", kb=kb, wants_draft=True)
    assert out["requires_approval"] is True    # §3.3 — nothing sends on its own
