"""Brain-hosted Google OAuth (Calendar + Gmail readonly scopes)."""

from __future__ import annotations

import os
import re
import secrets
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

BRAIN_DIR = Path(__file__).resolve().parents[2]
ENV_PATH = BRAIN_DIR / ".env"

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000/google/oauth/callback"
LEGACY_REDIRECT_URI = "http://localhost:8765/oauth2callback"
LEGACY_REDIRECT_PORT = 8765
TOKEN_URL = "https://oauth2.googleapis.com/token"
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_CREDENTIALS_URL = "https://console.cloud.google.com/apis/credentials"

_STATE_TTL_SEC = 600.0
_pending_states: dict[str, float] = {}
_legacy_server_started = False


def redirect_uri() -> str:
    return (os.getenv("GOOGLE_OAUTH_REDIRECT_URI") or DEFAULT_REDIRECT_URI).strip()


def legacy_redirect_uri() -> str:
    return LEGACY_REDIRECT_URI


def has_client_credentials() -> bool:
    return bool(os.getenv("GOOGLE_CLIENT_ID", "").strip()) and bool(
        os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    )


def has_refresh_token() -> bool:
    return bool(os.getenv("GOOGLE_REFRESH_TOKEN", "").strip())


def reload_env() -> None:
    """Re-read GOOGLE_* keys from .env into os.environ (after writes)."""
    if not ENV_PATH.is_file():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.startswith("GOOGLE_"):
            os.environ[key] = val


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


def save_client_credentials(client_id: str, client_secret: str) -> None:
    cid = client_id.strip()
    secret = client_secret.strip()
    if not cid or not secret:
        raise ValueError("Client ID and secret are required.")
    if not cid.endswith(".apps.googleusercontent.com"):
        raise ValueError("Client ID should end with .apps.googleusercontent.com")
    set_env_var("GOOGLE_CLIENT_ID", cid)
    set_env_var("GOOGLE_CLIENT_SECRET", secret)
    if not os.getenv("GOOGLE_CALENDAR_ID", "").strip():
        set_env_var("GOOGLE_CALENDAR_ID", "primary")
    if not os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "").strip():
        set_env_var("GOOGLE_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI)


def oauth_status() -> dict:
    return {
        "has_client_id": bool(os.getenv("GOOGLE_CLIENT_ID", "").strip()),
        "has_client_secret": bool(os.getenv("GOOGLE_CLIENT_SECRET", "").strip()),
        "has_refresh_token": has_refresh_token(),
        "redirect_uri": redirect_uri(),
        "legacy_redirect_uri": legacy_redirect_uri(),
        "ready_to_connect": has_client_credentials() and not has_refresh_token(),
        "connected": has_client_credentials() and has_refresh_token(),
        "credentials_url": GOOGLE_CREDENTIALS_URL,
    }


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


def exchange_code(code: str, *, callback_redirect_uri: str | None = None) -> dict:
    uri = callback_redirect_uri or redirect_uri()
    resp = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "redirect_uri": uri,
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
    reload_env()


def _page_shell(title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:40rem;margin:2rem auto;line-height:1.55;color:#111}}
code,pre{{background:#f4f4f5;padding:.15rem .35rem;border-radius:4px;font-size:.92em}}
pre{{padding:.75rem;overflow-x:auto}}
.step{{margin:1.25rem 0;padding:1rem;border:1px solid #e4e4e7;border-radius:8px}}
.step h3{{margin:.2rem 0 .6rem;font-size:1rem}}
label{{display:block;margin:.5rem 0 .25rem;font-weight:600}}
input[type=text],input[type=password]{{width:100%;padding:.5rem;border:1px solid #d4d4d8;border-radius:6px;box-sizing:border-box}}
button,.btn{{display:inline-block;margin-top:.75rem;padding:.55rem 1rem;background:#18181b;color:#fff;border:none;border-radius:6px;text-decoration:none;cursor:pointer;font-size:.95rem}}
button:hover,.btn:hover{{background:#27272a}}
.msg{{padding:.75rem;border-radius:6px;margin:.75rem 0}}
.msg.ok{{background:#ecfdf5;color:#065f46}}
.msg.err{{background:#fef2f2;color:#991b1b}}
</style></head>
<body>{body}</body></html>"""


def setup_wizard_html(*, saved: bool = False, error: str | None = None) -> str:
    uri = redirect_uri()
    legacy = legacy_redirect_uri()
    status = oauth_status()
    msg = ""
    if error:
        safe = error.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        msg = f'<div class="msg err">{safe}</div>'
    elif saved:
        msg = '<div class="msg ok">Credentials saved. Click Connect Google below.</div>'

    connect_block = ""
    if status["has_client_id"] and status["has_client_secret"]:
        connect_block = """
<div class="step">
<h3>Step 4 — Sign in with Google</h3>
<p>One click opens Google consent. Approve access for Calendar (read) and Gmail (read).</p>
<a class="btn" href="/connect/google?start=1">Connect Google</a>
</div>"""

    return _page_shell(
        "Connect Google Calendar + Gmail",
        f"""<h2>Connect Google Calendar + Gmail</h2>
<p>Brain needs an OAuth client from Google Cloud — not a service account. This wizard saves credentials to <code>.env</code> for you.</p>
{msg}
<div class="step">
<h3>Step 1 — Google Cloud Console</h3>
<p><a href="{GOOGLE_CREDENTIALS_URL}" target="_blank" rel="noopener">Open Credentials</a> → create or select a project → enable <strong>Google Calendar API</strong> and <strong>Gmail API</strong> → OAuth consent screen (add yourself as test user) → Create <strong>OAuth client ID</strong> (Desktop or Web).</p>
</div>
<div class="step">
<h3>Step 2 — Authorized redirect URI</h3>
<p>Add this URI to your OAuth client (recommended):</p>
<pre>{uri}</pre>
<p>Legacy CLI port (Brain now listens here too):</p>
<pre>{legacy}</pre>
</div>
<div class="step">
<h3>Step 3 — Paste client credentials</h3>
<form method="post" action="/connect/google/config/form">
<label for="client_id">Client ID</label>
<input id="client_id" name="client_id" type="text" placeholder="….apps.googleusercontent.com" autocomplete="off" required>
<label for="client_secret">Client secret</label>
<input id="client_secret" name="client_secret" type="password" placeholder="GOCSPX-…" autocomplete="off" required>
<button type="submit">Save credentials</button>
</form>
</div>
{connect_block}
<p><a href="/">← Command Center</a></p>""",
    )


def missing_credentials_html() -> str:
    return setup_wizard_html()


def success_html() -> str:
    return _page_shell(
        "Google connected",
        """<h2>Google Calendar + Gmail connected</h2>
<p>Refresh token saved. Calendar and Gmail are live in the Brain.</p>
<p><a class="btn" href="/">Return to Command Center</a></p>""",
    )


def error_html(message: str, *, detail: str | None = None) -> str:
    safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    extra = ""
    if detail:
        d = detail.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        extra = f"<p><small>{d}</small></p>"
    return _page_shell(
        "Google OAuth error",
        f"""<h2>Could not connect Google</h2>
<p>{safe}</p>
{extra}
<p>Check that your OAuth client redirect URI matches:</p>
<pre>{redirect_uri()}</pre>
<p><a class="btn" href="/connect/google">Try again</a></p>""",
    )


def legacy_trap_html() -> str:
    brain = "http://127.0.0.1:8000/connect/google"
    return _page_shell(
        "Use Brain OAuth flow",
        f"""<h2>Google OAuth — use the Brain flow</h2>
<p>Port 8765 is handled by Brain. If you registered the legacy redirect URI, sign-in from here still works when you complete OAuth in the browser.</p>
<p><strong>Recommended:</strong> use the Brain-hosted flow instead:</p>
<p><a class="btn" href="{brain}">{brain}</a></p>
<p>Add this redirect URI in Google Cloud if you have not already:</p>
<pre>{redirect_uri()}</pre>""",
    )


def _handle_legacy_oauth_callback(query: str) -> bytes:
    qs = urllib.parse.parse_qs(query)
    if qs.get("error"):
        body = error_html(f"Google returned: {qs['error'][0]}")
        return body.encode("utf-8")
    code = qs.get("code", [""])[0]
    if not code:
        return legacy_trap_html().encode("utf-8")
    if not has_client_credentials():
        return missing_credentials_html().encode("utf-8")
    try:
        tokens = exchange_code(code, callback_redirect_uri=legacy_redirect_uri())
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:300] if exc.response else str(exc)
        return error_html("Token exchange failed on legacy port.", detail=detail).encode("utf-8")
    except Exception as exc:
        return error_html("Token exchange failed.", detail=str(exc)[:300]).encode("utf-8")
    refresh = tokens.get("refresh_token")
    if not refresh:
        return error_html(
            "No refresh token returned. Revoke app access at "
            "https://myaccount.google.com/permissions and try again with prompt=consent."
        ).encode("utf-8")
    persist_refresh_token(refresh)
    return success_html().encode("utf-8")


def start_legacy_callback_listener() -> None:
    """Listen on :8765 so old redirect URIs never hit connection refused."""
    global _legacy_server_started
    if _legacy_server_started:
        return
    _legacy_server_started = True

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/oauth2callback":
                body = _handle_legacy_oauth_callback(parsed.query)
            else:
                body = legacy_trap_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

    def run() -> None:
        try:
            server = HTTPServer(("127.0.0.1", LEGACY_REDIRECT_PORT), Handler)
            server.serve_forever()
        except OSError:
            pass

    threading.Thread(target=run, daemon=True, name="google-oauth-8765").start()
