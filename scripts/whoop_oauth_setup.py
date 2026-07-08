#!/usr/bin/env python3
"""
One-time Whoop OAuth desktop flow for persistent health metrics access.
Reads/writes goldfront-os/.env — never prints secret values to stdout.

Prerequisites:
  1. App registered at https://developer.whoop.com
  2. Redirect URI: http://localhost:8787/oauth2callback
  3. WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET in .env (or enter when prompted)

Usage:
  cd goldfront-os && python3 scripts/whoop_oauth_setup.py
"""

from __future__ import annotations

import os
import re
import secrets
import sys
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

BRAIN_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BRAIN_DIR / ".env"

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
REDIRECT_PORT = 8787
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/oauth2callback"

SCOPES = [
    "offline",
    "read:recovery",
    "read:cycles",
    "read:sleep",
    "read:workout",
    "read:profile",
]


def load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.is_file():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key] = val
    return env


def set_env_var(path: Path, key: str, value: str) -> None:
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


def prompt_secret(label: str, existing: str = "") -> str:
    if existing:
        use = input(f"{label} already in .env — use it? [Y/n]: ").strip().lower()
        if use in ("", "y", "yes"):
            return existing
    import getpass

    val = getpass.getpass(f"{label}: ").strip()
    return val


def exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    resp = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
            "scope": " ".join(SCOPES),
        },
        timeout=30.0,
    )
    if resp.status_code >= 400:
        print(f"Token exchange failed ({resp.status_code}): {resp.text[:200]}")
        sys.exit(1)
    return resp.json()


def main() -> None:
    env = load_dotenv(ENV_PATH)
    client_id = prompt_secret("WHOOP_CLIENT_ID", env.get("WHOOP_CLIENT_ID", ""))
    client_secret = prompt_secret("WHOOP_CLIENT_SECRET", env.get("WHOOP_CLIENT_SECRET", ""))
    if not client_id or not client_secret:
        print("Need WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET. Aborting.")
        sys.exit(1)

    set_env_var(ENV_PATH, "WHOOP_CLIENT_ID", client_id)
    set_env_var(ENV_PATH, "WHOOP_CLIENT_SECRET", client_secret)

    state = secrets.token_urlsafe(8)[:8]
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
    }
    auth_url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    print("\nOpening browser for Whoop sign-in…")
    print(f"If the browser does not open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    captured: dict[str, str] = {}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != "/oauth2callback":
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            if qs.get("state", [""])[0] != state:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"State mismatch")
                return
            if "error" in qs:
                captured["error"] = qs["error"][0]
            else:
                captured["code"] = qs.get("code", [""])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h2>Whoop connected.</h2>"
                b"<p>You can close this tab and return to the terminal.</p></body></html>"
            )

    server = HTTPServer(("127.0.0.1", REDIRECT_PORT), Handler)
    print(f"Waiting for OAuth callback on {REDIRECT_URI} …")
    server.handle_request()

    if captured.get("error"):
        print(f"OAuth error: {captured['error']}")
        sys.exit(1)
    code = captured.get("code", "")
    if not code:
        print("No authorization code received.")
        sys.exit(1)

    tokens = exchange_code(client_id, client_secret, code)
    refresh = tokens.get("refresh_token")
    if not refresh:
        print(
            "No refresh_token in response. Ensure the offline scope is enabled "
            "and re-run the flow."
        )
        sys.exit(1)

    set_env_var(ENV_PATH, "WHOOP_REFRESH_TOKEN", refresh)
    if tokens.get("access_token"):
        set_env_var(ENV_PATH, "WHOOP_ACCESS_TOKEN", tokens["access_token"])

    print("\n✓ WHOOP_REFRESH_TOKEN saved to .env (value not shown).")
    print("Brain will auto-refresh access tokens — no manual reconnect needed.")
    print("Restart brain, then verify:")
    print("  curl -s http://127.0.0.1:8000/connectors/status | python3 -m json.tool")


if __name__ == "__main__":
    main()
