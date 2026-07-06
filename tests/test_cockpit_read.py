"""Cockpit read layer — stable shapes + honest connect_source states."""

import pytest

from brain.cockpit.read import CockpitRead

CONNECTOR_ENV_KEYS = [
    "CLICKUP_API_TOKEN",
    "CLICKUP_WORKSPACE_ID",
    "FIELDY_API_TOKEN",
    "GHL_API_KEY",
    "GHL_LOCATION_ID",
    "WHOOP_ACCESS_TOKEN",
    "APPLE_HEALTH_EXPORT_PATH",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REFRESH_TOKEN",
]


@pytest.fixture
def no_connectors(monkeypatch):
    for k in CONNECTOR_ENV_KEYS:
        monkeypatch.delenv(k, raising=False)


def test_daily_brief_shape(kb):
    b = CockpitRead(kb).daily_brief()
    assert b["status"] in ("connect_source", "partial", "ok")
    assert isinstance(b["sources"], list)
    assert "today_schedule" in b
    assert "today" in b
    assert "watch_list" in b
    assert "accountability" in b
    assert "commitments_i_made" in b
    assert "top_money_moves" in b


def test_daily_brief_sections_single_connect_source(kb, no_connectors):
    """connect_source sections list one optional source — never bundled."""
    b = CockpitRead(kb).daily_brief()
    for key in (
        "today",
        "watch_list",
        "accountability",
        "commitments_i_made",
        "top_money_moves",
        "today_schedule",
        "commitments_owed",
    ):
        sec = b[key]
        if sec.get("status") == "connect_source":
            assert len(sec["sources"]) == 1, f"{key} bundled sources: {sec['sources']}"


def test_top_money_moves_shape(kb, no_connectors):
    m = CockpitRead(kb).top_money_moves(limit=5)
    assert m["limit"] == 5
    assert m["moves"] == []            # never fake data
    assert "decisions_known" in m
    if m["status"] == "connect_source":
        assert m["sources"] == ["clickup"]


def test_team_pulse_accountability_shape(kb, no_connectors):
    p = CockpitRead(kb).team_pulse()
    assert "overdue" in p and "gaps" in p
    assert p["status"] == "connect_source"
    assert p["sources"] == ["clickup"]


def test_blindspots_no_missing_connector_wall(kb, no_connectors):
    b = CockpitRead(kb).blindspots()
    assert b["status"] in ("connect_source", "ok")
    for item in b.get("items", []):
        title = (item.get("title") or "").lower()
        assert "not connected" not in title


def test_watchlist_empty_single_source(kb, no_connectors):
    w = CockpitRead(kb).watchlist()
    assert w["status"] == "connect_source"
    assert w["sources"] == ["brain_scan"]


def test_counts_reflect_memory(svc, kb):
    from brain.training.schemas import VoiceExampleIn

    svc.train_voice(VoiceExampleIn(text="hello", recipient="team", context="praise"))
    assert CockpitRead(kb).counts()["voice"] == 1


def test_connectors_status_endpoint_shape():
    from brain.connectors.status import connectors_status

    s = connectors_status()
    assert "connectors" in s
    assert "clickup" in s["connectors"]


def test_cockpit_http_endpoints_return_200(kb, no_connectors):
    from fastapi.testclient import TestClient

    from brain.main import app

    client = TestClient(app)
    paths = [
        "/brief/daily",
        "/money/top-moves",
        "/blindspots",
        "/watchlist",
        "/team/pulse",
        "/connectors/status",
        "/health/metrics",
        "/crm/ghl",
        "/calendar/week",
    ]
    for path in paths:
        resp = client.get(path)
        assert resp.status_code == 200, path
        body = resp.json()
        if "connectors" in body:
            continue
        assert body.get("status") in ("connect_source", "partial", "ok")
