"""Gmail connector (read-only counts + recent threads)."""

from __future__ import annotations

import httpx

from brain.connectors.base import ConnectorNotConfigured
from brain.connectors.google_auth import google_headers, is_google_configured

CONNECTOR = "gmail"
ENV_VARS = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]


def configured() -> bool:
    return is_google_configured()


def _gmail_get(path: str, params: dict | None = None) -> dict:
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    resp = httpx.get(
        f"https://gmail.googleapis.com/gmail/v1/users/me{path}",
        headers=google_headers(),
        params=params or {},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def _count_label(query: str) -> int:
    data = _gmail_get("/messages", {"q": query, "maxResults": 1})
    return int(data.get("resultSizeEstimate", 0))


def fetch_summary() -> dict:
    """Unread/starred counts + recent thread subjects (no send)."""
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    unread = _count_label("is:unread in:inbox")
    starred = _count_label("is:starred")

    threads_data = _gmail_get("/threads", {"q": "is:unread OR is:starred", "maxResults": 10})
    threads: list[dict] = []
    for tid in threads_data.get("threads", [])[:10]:
        detail = _gmail_get(f"/threads/{tid['id']}", {"format": "metadata"})
        headers = {}
        for msg in detail.get("messages", [])[:1]:
            for h in msg.get("payload", {}).get("headers", []):
                headers[h["name"].lower()] = h["value"]
        threads.append(
            {
                "id": tid["id"],
                "subject": headers.get("subject", "(no subject)"),
                "from": headers.get("from", ""),
                "source": "gmail",
            }
        )

    return {
        "unread_count": unread,
        "starred_count": starred,
        "recent_threads": threads,
    }


def commitment_threads() -> list[dict]:
    """Threads that may contain commitments (starred + recent unread)."""
    summary = fetch_summary()
    return [
        {
            "title": t["subject"],
            "detail": t.get("from", ""),
            "source": "gmail",
        }
        for t in summary.get("recent_threads", [])
    ]
