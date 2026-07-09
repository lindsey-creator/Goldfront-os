"""ClickUp task detail + comment endpoints — mocked API."""

import pytest

from brain.connectors import clickup
from brain.connectors.base import ConnectorNotConfigured


@pytest.fixture
def clickup_configured(monkeypatch):
    monkeypatch.setenv("CLICKUP_API_TOKEN", "pk_test_token")
    monkeypatch.setenv("CLICKUP_WORKSPACE_ID", "team99")


def test_fetch_task_detail_shapes_response(clickup_configured, monkeypatch):
    task = {
        "id": "task-1",
        "name": "Follow up with seller",
        "description": "Call before Friday",
        "url": "https://app.clickup.com/t/task-1",
        "due_date": "1700000000000",
        "status": {"status": "in progress", "type": "custom"},
        "assignees": [{"username": "aaron", "email": "aaron@example.com"}],
        "list": {"name": "Deals"},
        "space": {"name": "Rhino"},
        "folder": {},
        "tags": [],
        "custom_fields": [],
        "attachments": [],
    }
    comments = [
        {
            "id": "c2",
            "comment_text": "Latest note",
            "date": "1700001000000",
            "user": {"username": "lindsey"},
        },
        {
            "id": "c1",
            "comment_text": "Older note",
            "date": "1699999000000",
            "user": {"email": "ops@example.com"},
        },
    ]

    monkeypatch.setattr(clickup, "fetch_task", lambda _id: task)
    monkeypatch.setattr(clickup, "fetch_task_comments", lambda _id: comments)

    detail = clickup.fetch_task_detail("task-1")

    assert detail["id"] == "task-1"
    assert detail["name"] == "Follow up with seller"
    assert detail["description"] == "Call before Friday"
    assert detail["status"] == "in progress"
    assert detail["assignee"] == "aaron"
    assert detail["assignees"] == ["aaron"]
    assert detail["due_date"] == "2023-11-14"
    assert detail["url"] == "https://app.clickup.com/t/task-1"
    assert detail["list_name"] == "Deals"
    assert len(detail["comments"]) == 2
    assert detail["comments"][0]["text"] == "Latest note"
    assert detail["comments"][0]["author"] == "lindsey"
    assert detail["comments"][1]["author"] == "ops@example.com"


def test_fetch_task_detail_comments_failure_still_returns_task(
    clickup_configured, monkeypatch
):
    import httpx

    task = {
        "id": "task-2",
        "name": "No comments",
        "description": "",
        "status": {"status": "open"},
        "assignees": [],
        "list": {},
        "space": {},
        "folder": {},
        "tags": [],
        "custom_fields": [],
        "attachments": [],
    }

    monkeypatch.setattr(clickup, "fetch_task", lambda _id: task)

    def boom(_id):
        raise httpx.HTTPError("comments unavailable")

    monkeypatch.setattr(clickup, "list_task_comments", boom)

    detail = clickup.fetch_task_detail("task-2")

    assert detail["name"] == "No comments"
    assert detail["comments"] == []
    assert detail["assignee"] == "Unassigned"


def test_list_task_comments_alias(clickup_configured, monkeypatch):
    monkeypatch.setattr(
        clickup,
        "_get",
        lambda path: {"comments": [{"id": "c1", "comment_text": "hi"}]},
    )
    comments = clickup.list_task_comments("task-9")
    assert len(comments) == 1
    assert comments[0]["comment_text"] == "hi"


def test_get_task_endpoint_ok(clickup_configured, monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    monkeypatch.setattr(
        clickup,
        "fetch_task_detail",
        lambda task_id: {"id": task_id, "name": "Test task", "comments": []},
    )
    client = TestClient(app)
    resp = client.get("/clickup/tasks/task-42")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["task"]["id"] == "task-42"
    assert body["task"]["name"] == "Test task"


def test_get_task_endpoint_not_configured(monkeypatch):
    monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
    monkeypatch.delenv("CLICKUP_WORKSPACE_ID", raising=False)
    monkeypatch.setattr(clickup, "configured", lambda: False)
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    client = TestClient(app)
    resp = client.get("/clickup/tasks/abc")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "connect_source"
    assert body["sources"] == ["clickup"]


def test_comment_endpoint_ok(clickup_configured, monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    captured: dict = {}

    def fake_add_comment(task_id, text):
        captured["task_id"] = task_id
        captured["text"] = text
        return {"id": "c99"}

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    monkeypatch.setattr(clickup, "add_comment", fake_add_comment)
    client = TestClient(app)
    resp = client.post(
        "/clickup/tasks/task-7/comment",
        json={"text": "Please prioritize this week"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["comment"]["id"] == "c99"
    assert captured["task_id"] == "task-7"
    assert "Please prioritize this week" in captured["text"]


def test_comment_endpoint_requires_text(clickup_configured, monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    client = TestClient(app)
    resp = client.post("/clickup/tasks/task-7/comment", json={"text": "   "})
    assert resp.status_code == 400


def test_comment_endpoint_not_configured(monkeypatch):
    monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
    monkeypatch.delenv("CLICKUP_WORKSPACE_ID", raising=False)
    monkeypatch.setattr(clickup, "configured", lambda: False)
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    client = TestClient(app)
    resp = client.post(
        "/clickup/tasks/task-1/comment",
        json={"text": "hello"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "connect_source"


def test_fetch_task_detail_not_configured(monkeypatch):
    monkeypatch.delenv("CLICKUP_API_TOKEN", raising=False)
    monkeypatch.delenv("CLICKUP_WORKSPACE_ID", raising=False)
    monkeypatch.setattr(clickup, "configured", lambda: False)
    with pytest.raises(ConnectorNotConfigured):
        clickup.fetch_task_detail("1")


def test_clean_clickup_text_strips_mentions():
    raw = "[@Lindsey Conrad](#210163793) please review."
    assert clickup._clean_clickup_text(raw) == "@Lindsey Conrad please review."


def test_clean_clickup_text_strips_command_center_prefix():
    raw = "Instructions from Command Center:\nShip by Friday"
    assert clickup._clean_clickup_text(raw) == "Ship by Friday"


def test_fetch_task_detail_uses_folder_when_space_name_missing(
    clickup_configured, monkeypatch
):
    task = {
        "id": "task-3",
        "name": "Folder context",
        "description": "[@Ops](#1) check this",
        "status": {"status": "open"},
        "assignees": [],
        "list": {"name": "Deals"},
        "space": {"id": "space-only"},
        "folder": {"name": "Rhino Ops"},
        "tags": [],
        "custom_fields": [],
        "attachments": [],
    }

    monkeypatch.setattr(clickup, "fetch_task", lambda _id: task)
    monkeypatch.setattr(clickup, "list_task_comments", lambda _id: [])

    detail = clickup.fetch_task_detail("task-3")

    assert detail["space_name"] == "Rhino Ops"
    assert detail["description"] == "@Ops check this"
