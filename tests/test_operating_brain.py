"""Operating Brain loader + Echo persona integration."""

from brain.operating.loader import load_operating_brain, operating_brain_loaded
from brain.persona.persona import build_persona_prompt


def test_operating_brain_loads_all_parts():
    assert operating_brain_loaded()
    doc = load_operating_brain()
    assert doc.startswith("# OPERATING BRAIN")
    for part in range(1, 10):
        assert f"PART {part}" in doc
    assert "Echo" in doc
    assert "90141259054" in doc
    assert "FFdZCVGXSQQThtHZEOYx" in doc


def test_persona_echo_and_compliance_gates(monkeypatch):
    monkeypatch.setenv("GOLDFRONT_OWNER", "lindsey")
    p = build_persona_prompt()
    assert "Echo" in p
    assert "Task-assignment gate" in p
    assert "Rhino Robot" in p
    assert "Stone Donut" in p
    assert "RESPA" in p
    assert "TCPA" in p or "A2P" in p
    assert "voice-to-text" in p.lower() or "Voice-to-text" in p
    assert "OPERATING BRAIN" in p
