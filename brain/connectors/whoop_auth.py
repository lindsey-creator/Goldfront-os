"""Whoop OAuth2 access token via refresh token (httpx only)."""

from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured

TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

_TOKEN_CACHE: dict[str, object] = {"token": None, "expires_at": 0.0}
_REFRESH_LOCK = threading.Lock()

OAUTH_ENV_VARS = ["WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET", "WHOOP_REFRESH_TOKEN"]
LEGACY_ENV_VARS = ["WHOOP_ACCESS_TOKEN"]


def is_oauth_configured() -> bool:
    return is_configured(*OAUTH_ENV_VARS)


def is_legacy_configured() -> bool:
    return is_configured("WHOOP_ACCESS_TOKEN") and not is_oauth_configured()


def is_whoop_configured() -> bool:
    return is_oauth_configured() or is_legacy_configured()


def has_orphaned_refresh_token() -> bool:
    """Refresh token saved without client ID/secret — cannot refresh until fixed."""
    return is_configured("WHOOP_REFRESH_TOKEN") and not is_configured(
        "WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET"
    )


def setup_note() -> str | None:
    if has_orphaned_refresh_token():
        return (
            "Refresh token is saved but WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET are "
            "missing — paste app credentials from developer.whoop.com (Connect Whoop below)."
        )
    if is_configured("WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET") and not is_configured(
        "WHOOP_REFRESH_TOKEN"
    ):
        return "Whoop app credentials saved — complete OAuth sign-in to get a refresh token."
    return None


def _persist_env_var(key: str, value: str) -> None:
    """Write rotated refresh token back to .env (never log values)."""
    if not ENV_PATH.is_file():
        return
    text = ENV_PATH.read_text(encoding="utf-8")
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    if pattern.search(text):
        text = pattern.sub(f"{key}={value}", text)
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text += f"{key}={value}\n"
    ENV_PATH.write_text(text, encoding="utf-8")
    os.environ[key] = value


def _refresh_access_token() -> str:
    env_required("WHOOP_CLIENT_ID", "whoop")
    env_required("WHOOP_CLIENT_SECRET", "whoop")
    env_required("WHOOP_REFRESH_TOKEN", "whoop")

    with _REFRESH_LOCK:
        now = time.time()
        cached = _TOKEN_CACHE.get("token")
        if cached and now < float(_TOKEN_CACHE.get("expires_at", 0)):
            return str(cached)

        resp = httpx.post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "refresh_token": os.environ["WHOOP_REFRESH_TOKEN"],
                "client_id": os.environ["WHOOP_CLIENT_ID"],
                "client_secret": os.environ["WHOOP_CLIENT_SECRET"],
                "scope": "offline",
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()
        token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        _TOKEN_CACHE["token"] = token
        _TOKEN_CACHE["expires_at"] = now + expires_in - 60

        new_refresh = data.get("refresh_token")
        if new_refresh and new_refresh != os.environ.get("WHOOP_REFRESH_TOKEN"):
            _persist_env_var("WHOOP_REFRESH_TOKEN", new_refresh)

        return token


def get_access_token() -> str:
    """Return a valid Whoop access token (OAuth refresh or legacy static token)."""
    if has_orphaned_refresh_token():
        raise ConnectorNotConfigured(
            "whoop",
            ["WHOOP_CLIENT_ID", "WHOOP_CLIENT_SECRET"],
        )
    if is_oauth_configured():
        return _refresh_access_token()
    if is_legacy_configured():
        return env_required("WHOOP_ACCESS_TOKEN", "whoop")
    raise ConnectorNotConfigured(
        "whoop",
        OAUTH_ENV_VARS + ["(or legacy WHOOP_ACCESS_TOKEN)"],
    )


def whoop_headers() -> dict[str, str]:
    if not is_whoop_configured():
        raise ConnectorNotConfigured(
            "whoop",
            OAUTH_ENV_VARS + LEGACY_ENV_VARS,
        )
    return {"Authorization": f"Bearer {get_access_token()}"}
