"""ClickUp → Brain collection routing."""

from brain.connectors.clickup_routing import (
    decision_metadata,
    is_voice_transcript,
    route_collection,
    voice_transcript_metadata,
)


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


def test_route_transcript_to_conversation_patterns():
    r = {
        "id": "4",
        "title": "07-02 Consultation: Onboarding",
        "text": "Meeting notes from Plaud recording.",
        "list_name": "📥 Inbox — Raw Transcripts",
        "folder_name": "Plaud Meeting Notes",
        "tags": [],
    }
    assert route_collection(r) == "conversation_patterns"
    assert is_voice_transcript(r)


def test_route_fieldy_archive_transcript():
    r = {
        "id": "5",
        "title": "🎙️ 05-26: Business Development Meeting",
        "text": "Full transcript here.",
        "list_name": "Archive — Raw Transcripts (Feb–May, legacy)",
        "record_kind": "voice_transcript",
    }
    assert route_collection(r) == "conversation_patterns"
    meta = voice_transcript_metadata(r)
    assert meta["kind"] == "voice_transcript"
