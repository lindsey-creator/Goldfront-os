from fastapi.testclient import TestClient

from brain.main import app


def test_health_includes_jarvis_command():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "goldfront-brain"
    assert body["command"] == "jarvis"
    assert body["glass"] == "conrad-command-center"
    assert "ui_built" in body
    assert "engines" in body
    assert set(body["engines"]) == {"claude", "grok", "muse"}
    assert isinstance(body["engines"]["claude"], bool)
    assert isinstance(body["engines"]["grok"], bool)
    assert isinstance(body["engines"]["muse"], bool)
    assert isinstance(body["xai"], bool)
    assert isinstance(body["anthropic"], bool)
    assert "ANTHROPIC_API_KEY" not in r.text
    assert "XAI_API_KEY" not in r.text
