"""Brain-hosted Whoop OAuth (recovery / health metrics)."""

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

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_DEV_URL = "https://developer.whoop.com"

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8000/whoop/oauth/callback"
LEGACY_REDIRECT_URI = "http://localhost:8787/oauth2callback"
LEGACY_REDIRECT_PORT = 8787

SCOPES = [
    "offline",
    "read:recovery",
    "read:cycles",
    "read:sleep",
    "read:workout",
    "read:profile",
]

_STATE_TTL_SEC = 600.0
_pending_states: dict[str, float] = {}
_legacy_server_started = False


def redirect_uri() -> str:
    return (os.getenv("WHOOP_OAUTH_REDIRECT_URI") or DEFAULT_REDIRECT_URI).strip()


def legacy_redirect_uri() -> str:
    return LEGACY_REDIRECT_URI


def has_client_credentials() -> bool:
    return bool(os.getenv("WHOOP_CLIENT_ID", "").strip()) and bool(
        os.getenv("WHOOP_CLIENT_SECRET", "").strip()
    )


def has_refresh_token() -> bool:
    return bool(os.getenv("WHOOP_REFRESH_TOKEN", "").strip())


def has_orphaned_refresh_token() -> bool:
    return has_refresh_token() and not has_client_credentials()


def reload_env() -> None:
    """Re-read WHOOP_* keys from .env into os.environ (after writes)."""
    if not ENV_PATH.is_file():
        return
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.startswith("WHOOP_"):
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
    set_env_var("WHOOP_CLIENT_ID", cid)
    set_env_var("WHOOP_CLIENT_SECRET", secret)
    if not os.getenv("WHOOP_OAUTH_REDIRECT_URI", "").strip():
        set_env_var("WHOOP_OAUTH_REDIRECT_URI", DEFAULT_REDIRECT_URI)


def oauth_status() -> dict:
    orphaned = has_orphaned_refresh_token()
    connected = has_client_credentials() and has_refresh_token()
    setup_note = None
    if orphaned:
        setup_note = (
            "Refresh token is saved but client ID and secret are missing. "
            "Paste your Whoop app credentials below — the saved refresh token "
            "will work once they are added."
        )
    elif has_client_credentials() and not has_refresh_token():
        setup_note = "App credentials saved — click Connect Whoop to sign in."

    return {
        "has_client_id": bool(os.getenv("WHOOP_CLIENT_ID", "").strip()),
        "has_client_secret": bool(os.getenv("WHOOP_CLIENT_SECRET", "").strip()),
        "has_refresh_token": has_refresh_token(),
        "has_orphaned_refresh_token": orphaned,
        "redirect_uri": redirect_uri(),
        "legacy_redirect_uri": legacy_redirect_uri(),
        "ready_to_connect": has_client_credentials() and not has_refresh_token(),
        "connected": connected,
        "credentials_url": WHOOP_DEV_URL,
        "setup_note": setup_note,
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
    client_id = os.environ["WHOOP_CLIENT_ID"]
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(code: str, *, callback_redirect_uri: str | None = None) -> dict:
    uri = callback_redirect_uri or redirect_uri()
    resp = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": os.environ["WHOOP_CLIENT_ID"],
            "client_secret": os.environ["WHOOP_CLIENT_SECRET"],
            "redirect_uri": uri,
            "grant_type": "authorization_code",
            "scope": " ".join(SCOPES),
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def persist_tokens(refresh_token: str, access_token: str | None = None) -> None:
    set_env_var("WHOOP_REFRESH_TOKEN", refresh_token)
    if access_token:
        set_env_var("WHOOP_ACCESS_TOKEN", access_token)
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
.msg.warn{{background:#fffbeb;color:#92400e}}
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
        if status["has_orphaned_refresh_token"]:
            msg = (
                '<div class="msg ok">Credentials saved. Your existing refresh token '
                "should work — refresh Connections in Command Center.</div>"
            )
        else:
            msg = '<div class="msg ok">Credentials saved. Click Connect Whoop below.</div>'
    elif status.get("setup_note"):
        safe = status["setup_note"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        msg = f'<div class="msg warn">{safe}</div>'

    connect_block = ""
    if status["has_client_id"] and status["has_client_secret"] and not status["connected"]:
        connect_block = """
<div class="step">
<h3>Step 4 — Sign in with Whoop</h3>
<p>One click opens Whoop consent. Approve read access for recovery, sleep, and strain.</p>
<a class="btn" href="/connect/whoop?start=1">Connect Whoop</a>
</div>"""
    elif status["connected"]:
        connect_block = """
<div class="step">
<h3>Whoop connected</h3>
<p>Refresh token is saved. Recovery metrics are live in the Brain.</p>
</div>"""

    return _page_shell(
        "Connect Whoop",
        f"""<h2>Connect Whoop</h2>
<p>Brain needs an OAuth app from the Whoop Developer Portal. This wizard saves credentials to <code>.env</code> for you.</p>
{msg}
<div class="step">
<h3>Step 1 — Whoop Developer Portal</h3>
<p><a href="{WHOOP_DEV_URL}" target="_blank" rel="noopener">Open developer.whoop.com</a> → create an app → copy <strong>Client ID</strong> and <strong>Client Secret</strong>.</p>
</div>
<div class="step">
<h3>Step 2 — Authorized redirect URI</h3>
<p>Add this URI to your Whoop app (recommended):</p>
<pre>{uri}</pre>
<p>Legacy CLI port (Brain listens here too):</p>
<pre>{legacy}</pre>
</div>
<div class="step">
<h3>Step 3 — Paste app credentials</h3>
<form method="post" action="/connect/whoop/config/form">
<label for="client_id">Client ID</label>
<input id="client_id" name="client_id" type="text" autocomplete="off" required>
<label for="client_secret">Client secret</label>
<input id="client_secret" name="client_secret" type="password" autocomplete="off" required>
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
        "Whoop connected",
        """<h2>Whoop connected</h2>
<p>Refresh token saved. Recovery metrics are live in the Brain.</p>
<p><a class="btn" href="/">Return to Command Center</a></p>""",
    )


def error_html(message: str, *, detail: str | None = None) -> str:
    safe = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    extra = ""
    if detail:
        d = detail.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        extra = f"<p><small>{d}</small></p>"
    return _page_shell(
        "Whoop OAuth error",
        f"""<h2>Could not connect Whoop</h2>
<p>{safe}</p>
{extra}
<p>Check that your app redirect URI matches:</p>
<pre>{redirect_uri()}</pre>
<p><a class="btn" href="/connect/whoop">Try again</a></p>""",
    )


def legacy_trap_html() -> bytes:
    brain = "http://127.0.0.1:8000/connect/whoop"
    return _page_shell(
        "Use Brain OAuth flow",
        f"""<h2>Whoop OAuth — use the Brain flow</h2>
<p>Port 8787 is handled by Brain. If you registered the legacy redirect URI, sign-in from here still works.</p>
<p><strong>Recommended:</strong> use the Brain-hosted flow instead:</p>
<p><a class="btn" href="{brain}">{brain}</a></p>
<p>Add this redirect URI in the Whoop dashboard if you have not already:</p>
<pre>{redirect_uri()}</pre>""",
    ).encode("utf-8")


def _handle_legacy_oauth_callback(query: str) -> bytes:
    qs = urllib.parse.parse_qs(query)
    if qs.get("error"):
        body = error_html(f"Whoop returned: {qs['error'][0]}")
        return body.encode("utf-8")
    code = qs.get("code", [""])[0]
    if not code:
        return legacy_trap_html()
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
            "No refresh token returned. Ensure the offline scope is enabled and try again."
        ).encode("utf-8")
    persist_tokens(refresh, tokens.get("access_token"))
    return success_html().encode("utf-8")


def start_legacy_callback_listener() -> None:
    """Listen on :8787 so old redirect URIs and the CLI script still work."""
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
                body = legacy_trap_html()
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

    threading.Thread(target=run, daemon=True, name="whoop-oauth-8787").start()
