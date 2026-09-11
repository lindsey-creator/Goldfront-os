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
