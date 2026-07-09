"""Live connector layer tests — mocked HTTP, not-configured paths."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from brain.connectors import apple_health, clickup, fieldy, gcal, ghl, gmail, whoop
from brain.connectors.base import ConnectorNotConfigured
from brain.connectors.status import connectors_status


@pytest.fixture(autouse=True)
def clear_connector_env(monkeypatch):
    """Ensure connectors start unconfigured unless a test sets vars."""
    keys = [
        "CLICKUP_API_TOKEN",
        "CLICKUP_WORKSPACE_ID",
        "FIELDY_API_TOKEN",
        "GHL_API_KEY",
        "GHL_LOCATION_ID",
        "WHOOP_ACCESS_TOKEN",
        "WHOOP_CLIENT_ID",
        "WHOOP_CLIENT_SECRET",
        "WHOOP_REFRESH_TOKEN",
        "APPLE_HEALTH_EXPORT_PATH",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
    ]
    for k in keys:
        monkeypatch.delenv(k, raising=False)


def test_connectors_status_all_disconnected():
    s = connectors_status()
    assert s["connected_count"] == 0
    assert s["total"] == 9
    assert s["connectors"]["clickup"]["connected"] is False
    assert "CLICKUP_API_TOKEN" in s["connectors"]["clickup"]["env_vars"]
    # Never expose secret values
    for c in s["connectors"].values():
        assert "sk-" not in str(c)


def test_clickup_not_configured():
    with pytest.raises(ConnectorNotConfigured) as exc:
        clickup.fetch_records()
    assert "clickup" in str(exc.value).lower()


def test_fieldy_not_configured():
    with pytest.raises(ConnectorNotConfigured):
        fieldy.fetch_conversations()


def test_ghl_not_configured():
    with pytest.raises(ConnectorNotConfigured):
        ghl.fetch_crm_summary()


def test_whoop_not_configured():
    with pytest.raises(ConnectorNotConfigured):
        whoop.fetch_recovery()


def test_gcal_not_configured():
    with pytest.raises(ConnectorNotConfigured):
        gcal.fetch_today()


def test_gmail_not_configured():
    with pytest.raises(ConnectorNotConfigured):
        gmail.fetch_summary()


def test_apple_health_not_configured():
    with pytest.raises(ConnectorNotConfigured):
        apple_health.fetch_metrics()


def test_clickup_fetch_tasks_and_overdue(monkeypatch):
    monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")
    monkeypatch.setenv("CLICKUP_WORKSPACE_ID", "90141259054")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "tasks": [
            {
                "id": "t1",
                "name": "Follow up Baker",
                "description": "Get comps",
                "url": "https://app.clickup.com/t/1",
                "status": {"status": "open"},
                "due_date": "1600000000000",
                "assignees": [{"username": "Aaron"}],
                "list": {"name": "Ops"},
                "folder": {"name": "Goldfront"},
                "space": {"name": "Team"},
                "tags": [],
            }
        ]
    }
    empty_resp = MagicMock()
    empty_resp.raise_for_status = MagicMock()
    empty_resp.json.return_value = {"tasks": []}

    with patch("httpx.get") as mock_get:
        mock_get.side_effect = lambda url, **kwargs: (
            empty_resp
            if kwargs.get("params", {}).get("page", 0) > 0
            else mock_resp
            if "/team/" in url and "/task" in url
            else empty_resp
        )
        tasks = clickup.fetch_tasks()
        assert len(tasks) == 1
        records = clickup.fetch_records()
        assert records[0]["type"] == "task"
        assert records[0]["text"]
        overdue = clickup.overdue_tasks()
        assert len(overdue) == 1
        assert overdue[0]["person"] == "Aaron"
        mock_get.assert_called()


def test_clickup_transcript_task_record(monkeypatch):
    monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")
    monkeypatch.setenv("CLICKUP_WORKSPACE_ID", "90141259054")

    transcript_task = {
        "id": "tx1",
        "name": "07-02 Consultation: Onboarding",
        "description": "",
        "url": "https://app.clickup.com/t/tx1",
        "date_created": "1783364023396",
        "list": {"name": "📥 Inbox — Raw Transcripts"},
        "folder": {"name": "Plaud Meeting Notes"},
        "space": {"name": "Team Space"},
        "tags": [],
        "custom_fields": [
            {
                "name": "Summary",
                "value": "- Onboarding planned.\n- Includes appraisal panel integration.",
            }
        ],
        "attachments": [],
    }
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"tasks": [transcript_task]}
    empty_resp = MagicMock()
    empty_resp.raise_for_status = MagicMock()
    empty_resp.json.return_value = {"tasks": []}

    with patch("httpx.get") as mock_get:
        mock_get.side_effect = lambda url, **kwargs: (
            empty_resp
            if kwargs.get("params", {}).get("page", 0) > 0
            else mock_resp
            if "/team/" in url and "/task" in url
            else empty_resp
        )
        records = clickup.fetch_records()
        assert len(records) == 1
        assert records[0]["record_kind"] == "voice_transcript"
        assert records[0]["collection"] == "conversation_patterns"
        assert "Onboarding planned" in records[0]["text"]
        convos = clickup.fetch_recent_transcripts(days_back=30)
        assert len(convos) == 1
        assert convos[0]["source"] == "clickup"


def test_fieldy_fetch_conversations(monkeypatch):
    monkeypatch.setenv("FIELDY_API_TOKEN", "fy_test")

    conv_resp = MagicMock()
    conv_resp.raise_for_status = MagicMock()
    conv_resp.json.return_value = {
        "items": [
            {
                "id": "c1",
                "title": "Call with Bobby",
                "startTime": "2026-07-04T10:00:00Z",
                "endTime": "2026-07-04T10:30:00Z",
                "content": "Lindsey: Let's close.\nBobby: Sounds good.",
            }
        ]
    }

    with patch("httpx.get", return_value=conv_resp):
        convos = fieldy.fetch_conversations()
        assert len(convos) == 1
        assert convos[0]["speaker_me"] == "Lindsey"
        assert "Let's close" in convos[0]["transcript"]


def test_ghl_fetch_summary(monkeypatch):
    monkeypatch.setenv("GHL_API_KEY", "ghl_test")
    monkeypatch.setenv("GHL_LOCATION_ID", "loc123")

    def fake_get(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "contacts" in url:
            resp.json.return_value = {
                "contacts": [
                    {
                        "id": "1",
                        "firstName": "Jane",
                        "lastName": "Doe",
                        "phone": "555-0100",
                        "dateAdded": "2026-07-01",
                    },
                    {"id": "2", "firstName": "John", "lastName": "Smith"},
                ]
            }
        elif "conversations" in url:
            resp.json.return_value = {
                "conversations": [{"unreadCount": 2, "lastMessageType": "missed_call"}]
            }
        else:
            resp.json.return_value = {"opportunities": [{"name": "Deal A", "status": "open"}]}
        return resp

    with patch("httpx.get", side_effect=fake_get):
        summary = ghl.fetch_crm_summary()
        assert summary["new_leads"] == 2
        assert len(summary["leads"]) == 2
        assert summary["leads"][0]["title"] == "Jane Doe"
        assert summary["unread_texts"] >= 0


def test_whoop_token_refresh(monkeypatch):
    monkeypatch.setenv("WHOOP_CLIENT_ID", "cid")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "secret")
    monkeypatch.setenv("WHOOP_REFRESH_TOKEN", "refresh")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "access_token": "at_whoop",
        "expires_in": 3600,
        "refresh_token": "refresh_new",
    }

    with patch("httpx.post", return_value=mock_resp):
        from brain.connectors.whoop_auth import get_access_token

        token = get_access_token()
        assert token == "at_whoop"


def test_whoop_orphaned_refresh_token(monkeypatch):
    monkeypatch.setenv("WHOOP_REFRESH_TOKEN", "orphaned")
    monkeypatch.delenv("WHOOP_CLIENT_ID", raising=False)
    monkeypatch.delenv("WHOOP_CLIENT_SECRET", raising=False)

    from brain.connectors.whoop_auth import get_access_token, has_orphaned_refresh_token, setup_note

    assert has_orphaned_refresh_token() is True
    assert setup_note() is not None
    with pytest.raises(ConnectorNotConfigured) as exc:
        get_access_token()
    assert "WHOOP_CLIENT_ID" in exc.value.env_vars


def test_whoop_fetch_recovery(monkeypatch):
    monkeypatch.setenv("WHOOP_CLIENT_ID", "cid")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "secret")
    monkeypatch.setenv("WHOOP_REFRESH_TOKEN", "refresh")

    token_resp = MagicMock()
    token_resp.raise_for_status = MagicMock()
    token_resp.json.return_value = {
        "access_token": "at_whoop",
        "expires_in": 3600,
    }

    recovery_resp = MagicMock()
    recovery_resp.raise_for_status = MagicMock()
    recovery_resp.json.return_value = {
        "records": [
            {
                "score": {
                    "recovery_score": 82,
                    "hrv_rmssd_milli": 45.2,
                    "resting_heart_rate": 52,
                    "sleep": {"total_in_bed_time_milli": 28800000},
                },
                "strain": 12.5,
            }
        ]
    }

    with patch("httpx.post", return_value=token_resp), patch(
        "httpx.get", return_value=recovery_resp
    ):
        data = whoop.fetch_recovery()
        assert data["recovery_score"] == 82
        assert data["hrv"] == 45.2
        assert data["source"] == "whoop"


def test_google_token_refresh(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_REFRESH_TOKEN", "refresh")

    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"access_token": "at_test", "expires_in": 3600}

    with patch("httpx.post", return_value=mock_resp):
        from brain.connectors.google_auth import get_access_token

        token = get_access_token()
        assert token == "at_test"


def test_apple_health_reads_export(tmp_path, monkeypatch):
    export = tmp_path / "health.json"
    export.write_text(
        json.dumps({"hrv": 45, "sleep_hours": 7.2, "strain": 12}),
        encoding="utf-8",
    )
    monkeypatch.setenv("APPLE_HEALTH_EXPORT_PATH", str(export))
    metrics = apple_health.fetch_metrics()
    assert metrics["hrv"] == 45
    assert metrics["source"] == "apple_health"


def test_clickup_ingest_live_wired(monkeypatch, svc):
    monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test")
    monkeypatch.setenv("CLICKUP_WORKSPACE_ID", "90141259054")

    with patch(
        "brain.connectors.clickup.fetch_records",
        return_value=[{"id": "d1", "type": "doc", "text": "Margin floor 30%"}],
    ):
        result = clickup.ingest_live(svc=svc)
        assert result["ingested"] == 1


def test_fieldy_ingest_live_wired(monkeypatch, svc):
    monkeypatch.setenv("FIELDY_API_TOKEN", "fy_test")

    with patch(
        "brain.connectors.fieldy.fetch_conversations",
        return_value=[
            {
                "id": "c1",
                "transcript": "Lindsey: Done.",
                "speaker_me": "Lindsey",
            }
        ],
    ):
        result = fieldy.ingest_live(svc=svc, days_back=1)
        assert result["voice_examples"] >= 1
