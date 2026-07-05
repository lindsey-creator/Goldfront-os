"""Heuristic classifier (Claude path not exercised in tests — no key)."""

from brain.training.classifier import CONTEXTS, RECIPIENTS, classify, _heuristic


def test_recipient_partner_beats_generic():
    assert _heuristic("Ken, we can't miss this funding date")["recipient"] == "partner"


def test_recipient_team():
    assert _heuristic("Emma, please handle the Titus file")["recipient"] == "team"


def test_recipient_client():
    assert _heuristic("Congratulations on your loan approval!")["recipient"] == "client"


def test_accountability_beats_closing_on_wire_tie():
    # 'wire' should no longer hijack an accountability message
    r = _heuristic("Ken dropped the ball on the wire again")
    assert r["context"] == "accountability"


def test_praise_detected():
    assert _heuristic("Aaron you crushed it, well done")["context"] == "praise"


def test_firing_detected():
    assert _heuristic("This isn't working out, your last day is Friday")["context"] == "firing"


def test_classify_returns_valid_labels():
    r = classify("some random business note")
    assert r["recipient"] in RECIPIENTS
    assert r["context"] in CONTEXTS
