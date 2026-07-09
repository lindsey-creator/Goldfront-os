"""ClickUp members + assign — mocked API."""

import pytest

from brain.connectors import clickup
from brain.connectors.base import ConnectorNotConfigured


@pytest.fixture
def clickup_configured(monkeypatch):
    monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test_token")
    monkeypatch.setenv("CLICKUP_WORKSPACE_ID", "team99")


def test_fetch_team_members_filters_workspace(clickup_configured, monkeypatch):
    monkeypatch.setattr(
        clickup,
        "_get",
        lambda path, params=None: {
            "teams": [
                {
                    "id": "other",
                    "members": [{"user": {"id": 1, "username": "other"}}],
                },
                {
                    "id": "team99",
                    "members": [
                        {"user": {"id": 42, "username": "Aaron", "email": "a@test.com"}},
                        {"user": {"id": 7, "username": "Ken", "email": "k@test.com"}},
                    ],
                },
            ]
        },
    )

    members = clickup.fetch_team_members()

    assert len(members) == 2
    assert members[0]["id"] == "42"
    assert members[0]["name"] == "Aaron"
    assert members[1]["email"] == "k@test.com"


def test_assign_task_puts_assignees(clickup_configured, monkeypatch):
    captured: dict = {}

    def fake_put(path, body):
        captured["path"] = path
        captured["body"] = body
        return {"id": "t1"}

    monkeypatch.setattr(clickup, "_put", fake_put)

    clickup.assign_task("t1", "42")

    assert captured["path"] == "/task/t1"
    assert captured["body"] == {"assignees": {"add": [42], "rem": []}}


def test_members_endpoint_not_configured(monkeypatch):
    monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
    monkeypatch.delenv("CLICKUP_WORKSPACE_ID", raising=False)
    monkeypatch.setattr(clickup, "configured", lambda: False)
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    client = TestClient(app)
    resp = client.get("/clickup/members")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "connect_source"
    assert body["members"] == []


def test_assign_endpoint_ok(clickup_configured, monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    monkeypatch.setattr(
        clickup,
        "assign_task",
        lambda task_id, member_id: {"id": task_id, "assignees": [int(member_id)]},
    )

    client = TestClient(app)
    resp = client.post("/clickup/tasks/task-1/assign", json={"member_id": "42"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["task"]["id"] == "task-1"


def test_not_configured_raises_assign(monkeypatch):
    monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
    monkeypatch.delenv("CLICKUP_WORKSPACE_ID", raising=False)
    monkeypatch.setattr(clickup, "configured", lambda: False)
    with pytest.raises(ConnectorNotConfigured):
        clickup.assign_task("1", "2")
