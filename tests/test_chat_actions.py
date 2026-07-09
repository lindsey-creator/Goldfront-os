"""Echo chat action parsing."""

from unittest.mock import MagicMock

import pytest

from brain.agent import chat_actions


def test_sync_clickup_phrase(monkeypatch):
    monkeypatch.setattr(chat_actions.clickup, "configured", lambda: True)
    monkeypatch.setattr(
        chat_actions,
        "maybe_sync",
        lambda force=False: {"ingested": 12, "records_fetched": 40},
    )

    result = chat_actions.try_chat_action("Please sync ClickUp now")

    assert result is not None
    assert result["action"] == "sync_clickup"
    assert result["action_status"] == "ok"
    assert "12 items" in result["answer"]


def test_sync_clickup_not_connected(monkeypatch):
    monkeypatch.setattr(chat_actions.clickup, "configured", lambda: False)

    result = chat_actions.try_chat_action("sync clickup")

    assert result["action_status"] == "connect_source"


def test_complete_task_phrase(monkeypatch):
    monkeypatch.setattr(chat_actions.clickup, "configured", lambda: True)
    monkeypatch.setattr(
        chat_actions.clickup,
        "complete_task",
        lambda task_id: {"id": task_id},
    )

    result = chat_actions.try_chat_action("mark task abc123xyz done")

    assert result is not None
    assert result["action"] == "complete_task"
    assert result["action_status"] == "ok"
    assert "abc123xyz" in result["answer"]


def test_complete_task_error(monkeypatch):
    monkeypatch.setattr(chat_actions.clickup, "configured", lambda: True)

    def boom(_id):
        raise RuntimeError("not found")

    monkeypatch.setattr(chat_actions.clickup, "complete_task", boom)

    result = chat_actions.try_chat_action("complete task badtask99")

    assert result["action_status"] == "error"


def test_no_match_returns_none():
    assert chat_actions.try_chat_action("what are my priorities today?") is None


def test_chat_endpoint_runs_action(monkeypatch):
    from fastapi.testclient import TestClient

    from brain.main import app

    monkeypatch.setattr("brain.main.startup_clickup_sync", lambda: None)
    monkeypatch.setattr(
        chat_actions,
        "try_chat_action",
        lambda msg: {"answer": "Action ran.", "mode": "action", "action": "test"},
    )

    client = TestClient(app)
    resp = client.post("/chat", json={"message": "sync clickup"})
    assert resp.status_code == 200
    assert resp.json()["mode"] == "action"
