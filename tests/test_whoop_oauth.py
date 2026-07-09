"""Brain-hosted Whoop OAuth endpoints."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from brain.connectors import whoop_oauth
from brain.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_whoop_env(monkeypatch):
    for key in (
        "WHOOP_CLIENT_ID",
        "WHOOP_CLIENT_SECRET",
        "WHOOP_REFRESH_TOKEN",
        "WHOOP_ACCESS_TOKEN",
        "WHOOP_OAUTH_REDIRECT_URI",
    ):
        monkeypatch.delenv(key, raising=False)
    whoop_oauth._pending_states.clear()


def test_connect_whoop_shows_wizard_when_missing_credentials(client):
    resp = client.get("/connect/whoop", follow_redirects=False)
    assert resp.status_code == 200
    assert "Step 3" in resp.text
    assert whoop_oauth.redirect_uri() in resp.text


def test_connect_whoop_status(client):
    resp = client.get("/connect/whoop/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_client_id"] is False
    assert data["redirect_uri"] == whoop_oauth.redirect_uri()


def test_connect_whoop_status_orphaned_refresh_token(client, monkeypatch):
    monkeypatch.setenv("WHOOP_REFRESH_TOKEN", "saved-refresh")
    resp = client.get("/connect/whoop/status")
    data = resp.json()
    assert data["has_orphaned_refresh_token"] is True
    assert data["connected"] is False
    assert data["setup_note"]


def test_connect_whoop_config_saves_credentials(client, monkeypatch, tmp_path):
    monkeypatch.setattr(whoop_oauth, "ENV_PATH", tmp_path / ".env")
    resp = client.post(
        "/connect/whoop/config",
        json={"client_id": "whoop-client-id", "client_secret": "whoop-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["has_client_id"] is True
    assert data["ready_to_connect"] is True
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "WHOOP_CLIENT_ID=whoop-client-id" in env_text
    assert "whoop-secret" in env_text


def test_connect_whoop_config_rejects_empty_credentials(client, monkeypatch, tmp_path):
    monkeypatch.setattr(whoop_oauth, "ENV_PATH", tmp_path / ".env")
    resp = client.post(
        "/connect/whoop/config",
        json={"client_id": "", "client_secret": ""},
    )
    assert resp.status_code == 400


def test_connect_whoop_redirects_when_configured(client, monkeypatch):
    monkeypatch.setenv("WHOOP_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "test-client-secret")
    resp = client.get("/connect/whoop?start=1", follow_redirects=False)
    assert resp.status_code == 302
    location = resp.headers["location"]
    assert location.startswith("https://api.prod.whoop.com/oauth/oauth2/auth")
    assert "client_id=test-client-id" in location
    assert "read%3Arecovery" in location or "read:recovery" in location


def test_oauth_callback_persists_refresh_token(client, monkeypatch, tmp_path):
    monkeypatch.setenv("WHOOP_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setattr(whoop_oauth, "ENV_PATH", tmp_path / ".env")

    state = whoop_oauth.create_oauth_state()

    def fake_exchange(code: str, *, callback_redirect_uri: str | None = None) -> dict:
        assert code == "auth-code-123"
        return {
            "refresh_token": "refresh-token-xyz",
            "access_token": "at",
        }

    with patch.object(whoop_oauth, "exchange_code", side_effect=fake_exchange):
        resp = client.get(
            "/whoop/oauth/callback",
            params={"code": "auth-code-123", "state": state},
        )

    assert resp.status_code == 200
    assert "connected" in resp.text.lower()
    env_text = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "WHOOP_REFRESH_TOKEN=refresh-token-xyz" in env_text
    assert "refresh-token-xyz" not in resp.text


def test_oauth_callback_rejects_bad_state(client, monkeypatch):
    monkeypatch.setenv("WHOOP_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "test-client-secret")
    resp = client.get(
        "/whoop/oauth/callback",
        params={"code": "auth-code-123", "state": "invalid"},
    )
    assert resp.status_code == 400
    assert "state" in resp.text.lower()


def test_orphaned_refresh_token_becomes_connected_after_config(client, monkeypatch, tmp_path):
    monkeypatch.setenv("WHOOP_REFRESH_TOKEN", "saved-refresh")
    monkeypatch.setattr(whoop_oauth, "ENV_PATH", tmp_path / ".env")
    (tmp_path / ".env").write_text("WHOOP_REFRESH_TOKEN=saved-refresh\n", encoding="utf-8")

    resp = client.post(
        "/connect/whoop/config",
        json={"client_id": "whoop-client-id", "client_secret": "whoop-secret"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["has_orphaned_refresh_token"] is False


def test_exchange_code_uses_redirect_uri(monkeypatch):
    monkeypatch.setenv("WHOOP_CLIENT_ID", "cid")
    monkeypatch.setenv("WHOOP_CLIENT_SECRET", "csecret")
    monkeypatch.setenv(
        "WHOOP_OAUTH_REDIRECT_URI",
        "http://127.0.0.1:8000/whoop/oauth/callback",
    )

    mock_response = httpx.Response(
        200,
        json={"refresh_token": "rt", "access_token": "at"},
        request=httpx.Request("POST", whoop_oauth.TOKEN_URL),
    )
    with patch("brain.connectors.whoop_oauth.httpx.post", return_value=mock_response) as mock_post:
        data = whoop_oauth.exchange_code("code123")
        assert data["refresh_token"] == "rt"
        assert mock_post.call_args[1]["data"]["redirect_uri"] == whoop_oauth.redirect_uri()
