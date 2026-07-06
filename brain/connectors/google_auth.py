"""Google OAuth2 access token via refresh token (httpx only — no google-auth dep)."""

from __future__ import annotations

import os
import time

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured

_TOKEN_CACHE: dict[str, object] = {"token": None, "expires_at": 0.0}


def is_google_configured() -> bool:
    return is_configured(
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GOOGLE_REFRESH_TOKEN",
    )


def get_access_token() -> str:
    """Return a valid Google access token, refreshing if needed."""
    env_required("GOOGLE_CLIENT_ID", "google")
    env_required("GOOGLE_CLIENT_SECRET", "google")
    env_required("GOOGLE_REFRESH_TOKEN", "google")

    now = time.time()
    cached = _TOKEN_CACHE.get("token")
    if cached and now < float(_TOKEN_CACHE.get("expires_at", 0)):
        return str(cached)

    resp = httpx.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    expires_in = int(data.get("expires_in", 3600))
    _TOKEN_CACHE["token"] = token
    _TOKEN_CACHE["expires_at"] = now + expires_in - 60
    return token


def google_headers() -> dict[str, str]:
    if not is_google_configured():
        raise ConnectorNotConfigured(
            "google",
            ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"],
        )
    return {"Authorization": f"Bearer {get_access_token()}"}
