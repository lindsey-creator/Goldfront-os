"""ClickUp → Brain collection routing."""

from brain.connectors.clickup_routing import decision_metadata, route_collection


def test_route_decisions_from_list_name():
    r = {
        "id": "1",
        "title": "123 Maple Akron",
        "text": "VERDICT: GO\nBaker loves the comps.",
        "list_name": "Deal Decisions",
        "tags": [],
    }
    assert route_collection(r) == "decisions"
    meta = decision_metadata(r)
    assert meta["verdict"] == "GO"
    assert "Maple" in meta["address"]


def test_route_knowledge_default():
    r = {"id": "2", "title": "Margin rules", "text": "Floor 25% vs ARV", "tags": []}
    assert route_collection(r) == "knowledge"


def test_route_voice_from_tag():
    r = {
        "id": "3",
        "title": "Follow-up script",
        "text": "Hey — looping back on the refi.",
        "tags": ["email template"],
    }
    assert route_collection(r) == "voice"
