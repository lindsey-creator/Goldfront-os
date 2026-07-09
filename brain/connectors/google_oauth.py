"""Brain-hosted Google OAuth (Calendar + Gmail readonly scopes)."""

from __future__ import annotations

import os
import re
import secrets
import time
import urllib.parse
from pathlib import Path

import httpx

BRAIN_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BRAIN_DIR / ".env"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000/google/oauth/callback"
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"

_STATE_TTL_SEC = 600.0
_pending_states: dict[str, float] = {}


def redirect_uri() -> str:
    return (os.getenv("GOOGLE_OAUTH_REDIRECT_URI") or DEFAULT_REDIRECT_URI).strip()


def has_client_credentials() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID", "").strip()) and bool(
        os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    )


def set_env_var(key: str, value: str) -> None:
    """Update goldfront-os/.env without logging secret values."""
    path = ENV_PATH
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(f"{key}={value}", text)
        else:
            if text and not text.endswith("\n"):
                text += "\n"
            text += f"{key}={value}\n"
        path.write_text(text, encoding="utf-8")
    else:
        path.write_text(f"{key}={value}\n", encoding="utf-8")
    os.environ[key] = value


def _prune_states(now: float) -> None:
    expired = [s for s, ts in _pending_states.items() if now - ts > _STATE_TTL_SEC]
    for s in expired:
        del _pending_states[s]


def create_oauth_state() -> str:
    now = time.time()
    _prune_states(now)
    state = secrets.token_urlsafe(24)
    _pending_states[state] = now
    return state


def verify_oauth_state(state: str) -> bool:
    now = time.time()
    _prune_states(now)
    ts = _pending_states.pop(state, None)
    return ts is not None and now - ts <= _STATE_TTL_SEC


def build_authorization_url(state: str) -> str:
    client_id = os.environ["GOOGLE_CLIENT_ID"]
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(code: str) -> dict:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uri": redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def persist_refresh_token(refresh_token: str) -> None:
    set_env_var("GOOGLE_REFRESH_TOKEN", refresh_token)
    if not os.getenv("GOOGLE_CALENDAR_ID", "").strip():
        set_env_var("GOOGLE_CALENDAR_ID", "primary")


def missing_credentials_html() -> str:
    uri = redirect_uri()
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Google OAuth setup</title></head>
<body style="font-family:system-ui,sans-serif;max-width:36rem;margin:2rem auto;line-height:1.5">
<h2>Google client credentials required</h2>
<p>Add these to <code>goldfront-os/.env</code>, then reload this page:</p>
<ul>
<li><code>GOOGLE_CLIENT_ID</code></li>
<li><code>GOOGLE_CLIENT_SECRET</code></li>
</ul>
<p>In Google Cloud Console → Credentials → your OAuth client, add this redirect URI:</p>
<p><code>{uri}</code></p>
<p><a href="/connect/google">Try again</a></p>
</body></html>"""


def success_html() -> str:
    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Google connected</title></head>
<body style="font-family:system-ui,sans-serif;max-width:36rem;margin:2rem auto;line-height:1.5">
<h2>Google Calendar + Gmail connected</h2>
<p>Refresh token saved. Calendar and Gmail are live in the Brain.</p>
<p><a href="/">Return to Command Center</a></p>
</body></html>"""


def error_html(message: str) -> str:
    safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Google OAuth error</title></head>
<body style="font-family:system-ui,sans-serif;max-width:36rem;margin:2rem auto;line-height:1.5">
<h2>Could not connect Google</h2>
<p>{safe}</p>
<p><a href="/connect/google">Try again</a></p>
</body></html>"""
