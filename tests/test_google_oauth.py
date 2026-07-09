"""Brain-hosted Google OAuth endpoints."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from brain.connectors import google_oauth
from brain.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_google_env(monkeypatch):
    for key in (
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
        "GOOGLE_OAUTH_REDIRECT_URI",
    ):
        monkeypatch.delenv(key, raising=False)
    google_oauth._pending_states.clear()


def test_connect_google_missing_credentials(client):
    resp = client.get("/connect/google", follow_redirects=False)
    assert resp.status_code == 400
    assert "GOOGLE_CLIENT_ID" in resp.text
    assert google_oauth.redirect_uri() in resp.text


def test_connect_google_redirects_when_configured(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    resp = client.get("/connect/google", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth")
    assert "client_id=test-client-id" in location
    assert "calendar.readonly" in location
    assert "gmail.readonly" in location


def test_oauth_callback_persists_refresh_token(client, monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(google_oauth, "ENV_PATH", tmp_path / ".env")

    state = google_oauth.create_oauth_state()

    def fake_exchange(code: str) -> dict:
        assert code == "auth-code-123"
        return {"refresh_token": "refresh-token-xyz", "access_token": "at"}

    with patch.object(google_oauth, "exchange_code", side_effect=fake_exchange):
        resp = client.get(
            "/google/oauth/callback",
            params={"code": "auth-code-123", "state": state},
        )

    assert resp.status_code == 200
    assert "connected" in resp.text.lower()
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "GOOGLE_REFRESH_TOKEN=refresh-token-xyz" in env_text
    assert "refresh-token-xyz" not in resp.text


def test_oauth_callback_rejects_bad_state(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    resp = client.get(
        "/google/oauth/callback",
        params={"code": "auth-code-123", "state": "invalid"},
    )
    assert resp.status_code == 400
    assert "state" in resp.text.lower()


def test_exchange_code_uses_redirect_uri(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "cid")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "csecret")
    monkeypatch.setenv(
        "GOOGLE_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/google/oauth/callback",
    )

    mock_response = httpx.Response(
        200,
        json={"refresh_token": "rt", "access_token": "at"},
        request=httpx.Request("POST", google_oauth.TOKEN_URL),
    )
    with patch("brain.connectors.google_oauth.httpx.post", return_value=mock_response) as mock_post:
        data = google_oauth.exchange_code("code123")
        assert data["refresh_token"] == "rt"
        assert mock_post.call_args[1]["data"]["redirect_uri"] == google_oauth.redirect_uri()
