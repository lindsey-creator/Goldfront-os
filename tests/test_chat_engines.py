"""Multi-model /chat routing + health engine flags (no live provider calls)."""

from __future__ import annotations

import threading
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from brain.agent import engines
from brain.main import app


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr("brain.main.startup_background", lambda: None)
    return TestClient(app)


def test_normalize_model_default_and_case():
    assert engines.normalize_model(None) == "claude"
    assert engines.normalize_model("") == "claude"
    assert engines.normalize_model("CLAUDE") == "claude"
    assert engines.normalize_model("Grok") == "grok"
    assert engines.normalize_model("xai") == "grok"
    assert engines.normalize_model("MUSE") == "muse"


def test_normalize_model_rejects_unknown():
    try:
        engines.normalize_model("chatgpt")
    except ValueError as exc:
        assert "claude" in str(exc)
        assert "grok" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_health_flags_never_include_secret_values(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-secret-do-not-leak")
    monkeypatch.setenv("XAI_API_KEY", "xai-secret-do-not-leak")
    monkeypatch.delenv("MUSE_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("MUSE_API_URL", raising=False)
    monkeypatch.delenv("MUSE_WEBHOOK", raising=False)

    flags = engines.health_flags()
    blob = str(flags)
    assert "sk-ant" not in blob
    assert "xai-secret" not in blob
    assert flags["engines"] == {"claude": True, "grok": True, "muse": False}
    assert flags["xai"] is True
    assert flags["anthropic"] is True
    assert flags["muse"] is False
    assert "grok" in flags["models"]
    assert "claude" in flags["models"]
    assert "muse" not in flags["models"]


def test_health_endpoint_advertises_engines(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("XAI_API_KEY", "xai-test")
    monkeypatch.delenv("MUSE_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("MUSE_API_URL", raising=False)
    monkeypatch.delenv("MUSE_WEBHOOK", raising=False)

    client = _client(monkeypatch)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["command"] == "jarvis"
    assert body["engines"]["claude"] is True
    assert body["engines"]["grok"] is True
    assert body["engines"]["muse"] is False
    assert body["xai"] is True
    assert body["anthropic"] is True
    assert "sk-ant-test" not in r.text
    assert "xai-test" not in r.text


def test_chat_grok_without_key_is_honest_not_claude(monkeypatch):
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("brain.agent.chat_actions.try_chat_action", lambda msg: None)

    client = _client(monkeypatch)
    r = client.post("/chat", json={"message": "ping", "model": "GROK"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "grok"
    assert body["answer"] is None
    assert "XAI_API_KEY" in (body.get("error") or "")
    assert "not Claude" in (body.get("note") or "")
    assert body.get("mode") != "claude"
    assert body.get("mode") != "fallback"


def test_chat_muse_without_webhook_is_honest(monkeypatch):
    monkeypatch.delenv("MUSE_WEBHOOK_URL", raising=False)
    monkeypatch.delenv("MUSE_API_URL", raising=False)
    monkeypatch.delenv("MUSE_WEBHOOK", raising=False)
    monkeypatch.setattr("brain.agent.chat_actions.try_chat_action", lambda msg: None)

    client = _client(monkeypatch)
    r = client.post("/chat", json={"message": "ping", "model": "muse"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "muse"
    assert body["answer"] is None
    assert "Muse link not connected" in (body.get("error") or body.get("note") or "")


def test_chat_claude_default_still_works_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("brain.agent.chat_actions.try_chat_action", lambda msg: None)

    client = _client(monkeypatch)
    r = client.post("/chat", json={"message": "What do you think?"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "fallback"
    assert "No deal numbers" in body["answer"]


def test_chat_unknown_model_honest_error(monkeypatch):
    monkeypatch.setattr("brain.agent.chat_actions.try_chat_action", lambda msg: None)
    client = _client(monkeypatch)
    r = client.post("/chat", json={"message": "hi", "model": "chatgpt"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "error"
    assert body["answer"] is None
    assert "claude" in (body.get("error") or "").lower()


def test_chat_grok_calls_xai_not_anthropic(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "xai-test-token")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("brain.agent.chat_actions.try_chat_action", lambda msg: None)

    class FakeResp:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "Grok lane live. Margin is engine-only."}}]}

    fake_client = MagicMock()
    fake_client.post = AsyncMock(return_value=FakeResp())
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    with patch("brain.agent.engines.httpx.AsyncClient", return_value=fake_client):
        client = _client(monkeypatch)
        r = client.post("/chat", json={"message": "status", "model": "grok"})

    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "grok"
    assert "Grok lane live" in (body.get("answer") or "")
    fake_client.post.assert_awaited()
    url = fake_client.post.await_args.args[0]
    assert url == engines.XAI_CHAT_URL
    sent = fake_client.post.await_args.kwargs["json"]
    assert sent["model"] == "grok-4"
    assert sent["messages"][0]["role"] == "system"
    auth = fake_client.post.await_args.kwargs["headers"]["Authorization"]
    assert auth.startswith("Bearer ")
    assert "xai-test-token" not in r.text


def test_health_stays_responsive_while_chat_is_slow(monkeypatch):
    """Talk Mode GET /health must not wait on a blocking Claude call."""
    import asyncio
    import time

    import anyio
    from httpx import ASGITransport, AsyncClient

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr("brain.agent.chat_actions.try_chat_action", lambda msg: None)
    monkeypatch.setattr("brain.main.startup_background", lambda: None)

    gate = threading.Event()

    def slow_claude(message, kb, engine, wants_draft):
        gate.set()
        time.sleep(1.2)
        return {"answer": "slow", "mode": "claude", "engine": engine, "draft": None}

    monkeypatch.setattr(engines, "_claude_sync", slow_claude)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            chat_task = asyncio.create_task(ac.post("/chat", json={"message": "hang check"}))
            await asyncio.to_thread(gate.wait, 2)
            if not gate.is_set():
                raise AssertionError("/chat never entered the LLM pool")
            t0 = time.monotonic()
            health = await ac.get("/health")
            elapsed = time.monotonic() - t0
            chat = await chat_task
            return health, chat, elapsed

    health, chat, elapsed = anyio.run(run)
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert elapsed < 0.75, f"/health blocked for {elapsed:.2f}s behind /chat"
    assert chat.status_code == 200
