"""Bulk, Apollo, ClickUp, and Fieldy importers."""

from brain.training.importers import apollo, bulk_messages, clickup_ingest, fieldy_ingest


# -- bulk messages ----------------------------------------------------------
def test_bulk_txt_one_per_line(svc):
    raw = "Aaron great job\nfollowing up on your loan\nlet's close, send the wire"
    s = bulk_messages.import_messages(raw, "txt", svc=svc)
    assert s["imported"] == 3
    assert svc.kb.count("voice") == 3


def test_bulk_txt_blank_line_separated(svc):
    raw = "First message\nspanning two lines\n\nSecond message here"
    s = bulk_messages.import_messages(raw, "txt", svc=svc)
    assert s["imported"] == 2


def test_bulk_csv_with_metadata(svc):
    raw = "message,recipient,context\n\"Nice work Emma\",team,praise\n\"Your loan is approved\",client,follow_up\n"
    s = bulk_messages.import_messages(raw, "csv", svc=svc)
    assert s["imported"] == 2
    assert s["by_recipient"].get("team") == 1
    assert s["by_recipient"].get("client") == 1


def test_bulk_json_list_of_strings_and_objects(svc):
    raw = '["plain string one", {"text": "object two", "recipient": "partner", "context": "delegation"}]'
    s = bulk_messages.import_messages(raw, "json", svc=svc)
    assert s["imported"] == 2


def test_bulk_jsonl(svc):
    raw = '{"text": "line one"}\n{"text": "line two", "context": "closing"}'
    s = bulk_messages.import_messages(raw, "jsonl", svc=svc)
    assert s["imported"] == 2


def test_bulk_fifty_messages_one_shot(svc):
    raw = "\n".join(f"message number {i}" for i in range(50))
    s = bulk_messages.import_messages(raw, "txt", svc=svc)
    assert s["imported"] == 50
    assert svc.kb.count("voice") == 50


# -- apollo -----------------------------------------------------------------
def test_apollo_import_routes_sent_and_exchange(svc):
    raw = (
        "First Name,Last Name,Email,Company,Title,Email Body,Reply\n"
        "John,Doe,john@abc.com,ABC Capital,Investor,"
        "\"Are you looking to move on the 8-door?\",\"Price seems high\"\n"
    )
    s = apollo.import_apollo(raw, svc=svc)
    assert s["voice_examples"] == 1          # sent -> voice
    assert s["conversation_patterns"] == 1   # exchange -> conversation_patterns
    assert svc.kb.count("voice") == 1
    assert svc.kb.count("conversation_patterns") == 1


def test_apollo_flexible_headers_and_skips_empty(svc):
    raw = (
        "Contact Name,Company Name,Sent Message,Response\n"
        "Jane Smith,XYZ,\"Following up on the DSCR refi\",\"Let's talk\"\n"
        ",,,\n"  # empty row -> skipped
    )
    s = apollo.import_apollo(raw, svc=svc)
    assert s["voice_examples"] == 1
    assert s["conversation_patterns"] == 1
    assert s["skipped"] == 1


# -- clickup ----------------------------------------------------------------
def test_clickup_ingest_routes_to_knowledge(svc):
    records = [
        {"id": "t1", "type": "doc", "title": "Deal Rules", "text": "Margin floor 25% vs ARV", "url": "http://x"},
        {"id": "t2", "type": "task", "text": "Follow Baker's comp checklist"},
        {"id": "t3", "type": "comment", "text": ""},  # empty -> skipped
    ]
    s = clickup_ingest.ingest_records(records, svc=svc)
    assert s["ingested"] == 2
    assert s["skipped"] == 1
    assert svc.kb.count("knowledge") == 1
    assert svc.kb.count("decisions") == 1


def test_clickup_ingest_dedup(svc):
    records = [
        {"id": "t1", "type": "doc", "title": "Deal Rules", "text": "Margin floor 25%"},
    ]
    first = clickup_ingest.ingest_records(records, svc=svc)
    second = clickup_ingest.ingest_records(records, svc=svc)
    assert first["ingested"] == 1
    assert second["ingested"] == 0
    assert second["duplicated"] == 1


def test_clickup_ingest_routes_decisions(svc):
    records = [
        {
            "id": "d1",
            "type": "task",
            "title": "456 Oak Cleveland",
            "text": "VERDICT: CONDITIONAL\nThin on margin but Baker wants it.",
            "list_name": "Pipeline Decisions",
        },
    ]
    s = clickup_ingest.ingest_records(records, svc=svc)
    assert s["by_collection"]["decisions"] == 1
    assert svc.kb.count("decisions") == 1


def test_clickup_fetch_and_ingest_with_injected_fetcher(svc):
    def fake_fetcher():
        return [{"id": "d1", "type": "doc", "text": "CB3 is preferred DSCR takeout"}]

    s = clickup_ingest.fetch_and_ingest(fake_fetcher, svc=svc)
    assert s["ingested"] == 1


# -- fieldy -----------------------------------------------------------------
def test_fieldy_ingest_transcript_and_my_lines(svc):
    convos = [
        {
            "id": "c1",
            "title": "Call with Bobby",
            "date": "2026-07-04",
            "transcript": "Lindsey: What's the ARV?\nBobby: About 200k.\nLindsey: Then we're in.",
            "speaker_me": "Lindsey",
        }
    ]
    s = fieldy_ingest.ingest_conversations(convos, svc=svc)
    assert s["conversations"] == 1
    assert s["voice_examples"] == 2  # two Lindsey lines extracted
    assert svc.kb.count("conversation_patterns") == 1
    assert svc.kb.count("voice") == 2


def test_fieldy_explicit_utterances(svc):
    convos = [{"id": "c2", "my_utterances": ["We don't chase thin margins.", "Send it to Baker first."]}]
    s = fieldy_ingest.ingest_conversations(convos, svc=svc)
    assert s["voice_examples"] == 2
