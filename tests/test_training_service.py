"""Training service: voice, deal decisions (+divergence), team, conversation, history."""

import time

from brain.training.schemas import (
    ConversationPatternIn,
    DealDecisionIn,
    TeamInteractionIn,
    VoiceExampleIn,
)


def test_train_voice_autoclassifies(svc):
    r = svc.train_voice(VoiceExampleIn(text="Aaron, you crushed it — proud of you."))
    assert r["recipient"] == "team"
    assert r["context"] == "praise"
    assert svc.kb.count("voice") == 1


def test_train_voice_respects_provided_metadata(svc):
    r = svc.train_voice(VoiceExampleIn(text="hello", recipient="client", context="closing"))
    assert r["recipient"] == "client"
    assert r["context"] == "closing"
    assert r["classify_method"] == "provided"


def test_deal_decision_go_matches_rules(svc):
    # Strong margin + strong DSCR -> engine says GO, human says GO -> no divergence
    r = svc.train_deal_decision(
        DealDecisionIn(
            address="1 Strong St, Cleveland",
            purchase_price=80000,
            arv=200000,
            rehab_estimate=30000,
            monthly_rent=2000,
            monthly_debt_service=1200,
            verdict="GO",
            reasoning="Great comps from Baker",
        )
    )
    assert r["verdict"] == "GO"
    assert r["diverged"] is False
    assert svc.kb.count("decisions") == 1


def test_deal_decision_flags_divergence(svc):
    # Thin margin: all-in 190k vs ARV 200k -> 5% margin, engine will NOT say GO.
    # Human overrides to GO -> divergence must be flagged (spec §5.5).
    r = svc.train_deal_decision(
        DealDecisionIn(
            address="2 Thin Margin Ave, Akron",
            purchase_price=150000,
            arv=200000,
            rehab_estimate=40000,
            monthly_rent=900,
            monthly_debt_service=1000,
            verdict="GO",
            reasoning="Gut call — strategic relationship with Ken",
        )
    )
    assert r["verdict"] == "GO"
    assert r["rules_verdict"] != "GO"
    assert r["diverged"] is True
    assert "contradicts your own rules" in r["divergence_note"]


def test_verdict_normalization(svc):
    r = svc.train_deal_decision(
        DealDecisionIn(address="x", purchase_price=1, arv=10, verdict="pass", reasoning="")
    )
    assert r["verdict"] == "NO-GO"


def test_decisions_history_newest_first_and_recency_weighted(svc, kb):
    # Insert an old decision by back-dating its timestamp, then a fresh one.
    kb.add_decision("old", {"verdict": "NO-GO", "_ts": time.time() - 400 * 86400})
    svc.train_deal_decision(
        DealDecisionIn(address="new", purchase_price=1, arv=10, verdict="GO", reasoning="")
    )
    hist = svc.decisions_history()
    assert len(hist) == 2
    # newest first
    assert hist[0]["metadata"]["verdict"] == "GO"
    # recency: newer weight > older weight; old one decayed well below 1
    assert hist[0]["recency_weight"] > hist[1]["recency_weight"]
    assert hist[1]["recency_weight"] < 0.3


def test_decisions_history_filter_by_verdict(svc):
    svc.train_deal_decision(DealDecisionIn(address="a", purchase_price=1, arv=10, verdict="GO", reasoning=""))
    svc.train_deal_decision(DealDecisionIn(address="b", purchase_price=9, arv=10, verdict="NO-GO", reasoning=""))
    gos = svc.decisions_history(verdict="GO")
    assert len(gos) == 1
    assert gos[0]["metadata"]["verdict"] == "GO"


def test_team_interaction_category_constrained(svc):
    r = svc.train_team_interaction(
        TeamInteractionIn(
            person="Ken",
            situation="dropped the ball on the wire",
            response="Told him directly we can't miss funding dates.",
        )
    )
    assert r["category"] in (
        "coaching",
        "accountability",
        "praise",
        "delegation",
        "correction",
        "firing",
    )
    assert svc.kb.count("voice") == 1  # team interactions stored in voice


def test_conversation_stored(svc):
    svc.train_conversation(
        ConversationPatternIn(contact="John", company="ABC", thread="ME: ... THEM: ...")
    )
    assert svc.kb.count("conversation_patterns") == 1
