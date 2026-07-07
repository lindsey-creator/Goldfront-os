#!/usr/bin/env python3
"""
One-time Google OAuth desktop flow for Calendar + Gmail (readonly scopes).
Reads/writes goldfront-os/.env — never prints secret values to stdout.

Prerequisites:
  1. Google Cloud project with Calendar API + Gmail API enabled
  2. OAuth 2.0 Client ID (Desktop app) with redirect URI:
     http://localhost:8765/oauth2callback
  3. GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env (or enter when prompted)

Usage:
  cd goldfront-os && python3 scripts/google_oauth_setup.py
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

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
]
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/oauth2callback"


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
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=30.0,
    )
    if resp.status_code >= 400:
        print(f"Token exchange failed ({resp.status_code}): {resp.text[:200]}")
        sys.exit(1)
    return resp.json()


def main() -> None:
    env = load_dotenv(ENV_PATH)
    client_id = prompt_secret("GOOGLE_CLIENT_ID", env.get("GOOGLE_CLIENT_ID", ""))
    client_secret = prompt_secret("GOOGLE_CLIENT_SECRET", env.get("GOOGLE_CLIENT_SECRET", ""))
    if not client_id or not client_secret:
        print("Need GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET. Aborting.")
        sys.exit(1)

    set_env_var(ENV_PATH, "GOOGLE_CLIENT_ID", client_id)
    set_env_var(ENV_PATH, "GOOGLE_CLIENT_SECRET", client_secret)

    state = secrets.token_urlsafe(16)
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)

    print("\nOpening browser for Google sign-in (lindsey@theconradteam.com)…")
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
                b"<html><body><h2>Google connected.</h2>"
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
            "No refresh_token in response. Revoke app access at "
            "https://myaccount.google.com/permissions and re-run with prompt=consent."
        )
        sys.exit(1)

    set_env_var(ENV_PATH, "GOOGLE_REFRESH_TOKEN", refresh)
    if not env.get("GOOGLE_CALENDAR_ID"):
        set_env_var(ENV_PATH, "GOOGLE_CALENDAR_ID", "primary")

    print("\n✓ GOOGLE_REFRESH_TOKEN saved to .env (value not shown).")
    print("Restart brain, then verify:")
    print("  curl -s http://127.0.0.1:8000/connectors/status | python3 -m json.tool")


if __name__ == "__main__":
    main()
