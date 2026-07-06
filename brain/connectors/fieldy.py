"""Fieldy conversation connector."""

from __future__ import annotations

import os
from datetime import date, timedelta

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured

CONNECTOR = "fieldy"
ENV_VARS = ["FIELDY_API_TOKEN"]


def configured() -> bool:
    return is_configured(*ENV_VARS)


def _base_url() -> str:
    return os.getenv("FIELDY_API_BASE", "https://api.fieldy.ai").rstrip("/")


def _headers() -> dict[str, str]:
    token = env_required("FIELDY_API_TOKEN", CONNECTOR)
    return {"Authorization": f"Bearer {token}"}


def fetch_conversations(
    start: date | None = None,
    end: date | None = None,
) -> list[dict]:
    """
    Conversations shaped for fieldy_ingest.ingest_conversations:
    id, title, date, transcript, speaker_me.
    """
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    end = end or date.today()
    start = start or (end - timedelta(days=1))
    speaker_me = os.getenv("FIELDY_SPEAKER_ME", "Lindsey")

    resp = httpx.get(
        f"{_base_url()}/v1/conversations",
        headers=_headers(),
        params={"from": start.isoformat(), "to": end.isoformat()},
        timeout=60.0,
    )
    resp.raise_for_status()
    payload = resp.json()
    raw = payload if isinstance(payload, list) else payload.get("conversations", [])

    convos: list[dict] = []
    for c in raw:
        convos.append(
            {
                "id": c.get("id"),
                "title": c.get("title") or c.get("name", ""),
                "date": c.get("date") or c.get("created_at", "")[:10],
                "transcript": c.get("transcript") or c.get("text") or "",
                "my_utterances": c.get("my_utterances"),
                "speaker_me": c.get("speaker_me") or speaker_me,
            }
        )
    return convos


def fetch_yesterday() -> list[dict]:
    yesterday = date.today() - timedelta(days=1)
    return fetch_conversations(start=yesterday, end=yesterday)


def commitments_from_convos(convos: list[dict]) -> list[dict]:
    """Surface Lindsey's lines as commitment candidates (display only)."""
    from brain.training.importers.fieldy_ingest import _extract_my_lines

    items: list[dict] = []
    for c in convos:
        lines = c.get("my_utterances") or _extract_my_lines(
            c.get("transcript", ""), c.get("speaker_me")
        )
        for line in lines:
            items.append(
                {
                    "title": line[:120],
                    "detail": c.get("title", ""),
                    "date": c.get("date"),
                    "source": "fieldy",
                }
            )
    return items


def ingest_live(svc=None, days_back: int = 1) -> dict:
    """Wire live fetcher into fieldy_ingest.fetch_and_ingest."""
    from brain.training.importers import fieldy_ingest

    end = date.today()
    start = end - timedelta(days=days_back)

    def fetcher():
        return fetch_conversations(start=start, end=end)

    return fieldy_ingest.fetch_and_ingest(fetcher, svc)
