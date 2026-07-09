"""ClickUp task write methods — mocked API."""

from unittest.mock import MagicMock

import httpx
import pytest

from brain.connectors import clickup
from brain.connectors.base import ConnectorNotConfigured


@pytest.fixture
def clickup_configured(monkeypatch):
    monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test_token")
    monkeypatch.setenv("CLICKUP_WORKSPACE_ID", "90141259054")


def test_update_task_status_puts_status(clickup_configured, monkeypatch):
    captured: dict = {}

    def fake_put(path, body):
        captured["path"] = path
        captured["body"] = body
        return {"id": "abc123", "status": {"status": body["status"]}}

    monkeypatch.setattr(clickup, "_put", fake_put)

    result = clickup.update_task_status("abc123", "in progress")

    assert captured["path"] == "/task/abc123"
    assert captured["body"] == {"status": "in progress"}
    assert result["id"] == "abc123"


def test_complete_task_uses_list_closed_status(clickup_configured, monkeypatch):
    task = {
        "id": "t1",
        "list": {"id": "list99"},
        "status": {"status": "open", "type": "open"},
    }

    monkeypatch.setattr(clickup, "fetch_task", lambda _id: task)
    monkeypatch.setattr(
        clickup,
        "_get",
        lambda path, params=None: {
            "statuses": [
                {"status": "open", "type": "open"},
                {"status": "shipped", "type": "closed"},
            ]
        },
    )

    captured: dict = {}

    def fake_put(path, body):
        captured["body"] = body
        return {"id": "t1", "status": {"status": body["status"]}}

    monkeypatch.setattr(clickup, "_put", fake_put)

    clickup.complete_task("t1")

    assert captured["body"]["status"] == "shipped"


def test_complete_task_fallback_when_no_list(clickup_configured, monkeypatch):
    monkeypatch.setattr(
        clickup,
        "fetch_task",
        lambda _id: {"id": "t2", "list": {}, "status": {"status": "open"}},
    )
    captured: dict = {}

    def fake_put(path, body):
        captured["body"] = body
        return {"id": "t2"}

    monkeypatch.setattr(clickup, "_put", fake_put)

    clickup.complete_task("t2")

    assert captured["body"]["status"] == "complete"


def test_reopen_task_uses_list_open_status(clickup_configured, monkeypatch):
    task = {
        "id": "t3",
        "list": {"id": "list99"},
        "status": {"status": "complete", "type": "closed"},
    }

    monkeypatch.setattr(clickup, "fetch_task", lambda _id: task)
    monkeypatch.setattr(
        clickup,
        "_get",
        lambda path, params=None: {
            "statuses": [
                {"status": "to do", "type": "open"},
                {"status": "in progress", "type": "custom"},
                {"status": "complete", "type": "closed"},
            ]
        },
    )

    captured: dict = {}

    def fake_put(path, body):
        captured["body"] = body
        return {"id": "t3", "status": {"status": body["status"]}}

    monkeypatch.setattr(clickup, "_put", fake_put)

    clickup.reopen_task("t3")

    assert captured["body"]["status"] == "to do"


def test_reopen_task_does_not_normalize_status(clickup_configured, monkeypatch):
    """Resolved list status must be sent verbatim — not aliased to 'open'."""
    task = {
        "id": "t4",
        "list": {"id": "list99"},
        "status": {"status": "complete", "type": "closed"},
    }

    monkeypatch.setattr(clickup, "fetch_task", lambda _id: task)
    monkeypatch.setattr(
        clickup,
        "_get",
        lambda path, params=None: {
            "statuses": [{"status": "to do", "type": "open"}]
        },
    )
    captured: dict = {}

    def fake_put(path, body):
        captured["body"] = body
        return {"id": "t4"}

    monkeypatch.setattr(clickup, "_put", fake_put)

    clickup.reopen_task("t4")

    assert captured["body"]["status"] != "open"
    assert captured["body"]["status"] == "to do"


def test_reopen_task_fallback_when_no_list(clickup_configured, monkeypatch):
    monkeypatch.setattr(
        clickup,
        "fetch_task",
        lambda _id: {"id": "t5", "list": {}, "status": {"status": "complete"}},
    )
    captured: dict = {}

    def fake_put(path, body):
        captured["body"] = body
        return {"id": "t5"}

    monkeypatch.setattr(clickup, "_put", fake_put)

    clickup.reopen_task("t5")

    assert captured["body"]["status"] == "open"


def test_clickup_api_error_maps_to_400(clickup_configured, monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)

    def boom(*_a, **_k):
        raise clickup.ClickUpAPIError(
            "ClickUp API 400: invalid status",
            status_code=400,
            detail="invalid status",
        )

    monkeypatch.setattr(clickup, "reopen_task", boom)

    client = TestClient(app)
    resp = client.post("/clickup/tasks/bad/reopen")
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid status"


def test_clickup_reopen_endpoint_ok(clickup_configured, monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    monkeypatch.setattr(
        clickup,
        "reopen_task",
        lambda task_id: {"id": task_id, "status": {"status": "to do"}},
    )

    client = TestClient(app)
    resp = client.post("/clickup/tasks/task-42/reopen")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["task"]["id"] == "task-42"


def test_update_task_patch_name_and_status(clickup_configured, monkeypatch):
    captured: dict = {}

    def fake_put(path, body):
        captured["body"] = body
        return {"id": "x", **body}

    monkeypatch.setattr(clickup, "_put", fake_put)

    clickup.update_task("x", status="open", name="Renamed task")

    assert captured["body"] == {"status": "open", "name": "Renamed task"}


def test_add_comment_posts_text(clickup_configured, monkeypatch):
    captured: dict = {}

    def fake_post(path, body):
        captured["path"] = path
        captured["body"] = body
        return {"id": "c1"}

    monkeypatch.setattr(clickup, "_post", fake_post)

    clickup.add_comment("task42", "Done from Command Center")

    assert captured["path"] == "/task/task42/comment"
    assert captured["body"] == {"comment_text": "Done from Command Center"}


def test_not_configured_raises(monkeypatch):
    monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
    monkeypatch.delenv("CLICKUP_WORKSPACE_ID", raising=False)
    monkeypatch.setattr(clickup, "configured", lambda: False)
    with pytest.raises(ConnectorNotConfigured):
        clickup.update_task_status("1", "open")


def test_clickup_patch_endpoint_not_configured(monkeypatch):
    monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
    monkeypatch.delenv("CLICKUP_WORKSPACE_ID", raising=False)
    monkeypatch.setattr(clickup, "configured", lambda: False)
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    client = TestClient(app)
    resp = client.patch("/clickup/tasks/abc", json={"status": "complete"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "connect_source"
    assert body["sources"] == ["clickup"]


def test_clickup_complete_endpoint_ok(clickup_configured, monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    monkeypatch.setattr(
        clickup,
        "complete_task",
        lambda task_id: {"id": task_id, "status": {"status": "complete"}},
    )

    client = TestClient(app)
    resp = client.post("/clickup/tasks/task-99/complete")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["task"]["id"] == "task-99"


def test_clickup_patch_endpoint_api_error(clickup_configured, monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)

    def boom(*_a, **_k):
        raise clickup.ClickUpAPIError(
            "ClickUp API 400: invalid status",
            status_code=400,
            detail="invalid status",
        )

    monkeypatch.setattr(clickup, "update_task", boom)

    client = TestClient(app)
    resp = client.patch("/clickup/tasks/bad", json={"status": "nope"})
    assert resp.status_code == 400
    assert resp.json()["detail"] == "invalid status"
