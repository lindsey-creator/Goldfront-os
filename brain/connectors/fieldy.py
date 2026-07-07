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


def _api_root() -> str:
    base = os.getenv("FIELDY_API_BASE", "https://api.fieldy.ai").rstrip("/")
    if base.endswith("/api/public/v2"):
        return base
    return f"{base}/api/public/v2"


def _headers() -> dict[str, str]:
    token = env_required("FIELDY_API_TOKEN", CONNECTOR)
    return {"Authorization": f"Bearer {token}"}


def _timeout(*, quick: bool = False) -> httpx.Timeout:
    default = "8" if quick else os.getenv("FIELDY_REQUEST_TIMEOUT", "20")
    seconds = float(default)
    return httpx.Timeout(seconds, connect=min(5.0, seconds))


def _fallback_transcript(conv: dict) -> str:
    return (conv.get("summary") or conv.get("title") or "").strip()


def _range_params(start: date, end: date) -> dict[str, str]:
    return {
        "startTime": f"{start.isoformat()}T00:00:00Z",
        "endTime": f"{end.isoformat()}T23:59:59Z",
    }


def _get_paginated(
    path: str,
    params: dict[str, str],
    *,
    max_pages: int = 10,
    quick: bool = False,
) -> list[dict]:
    items: list[dict] = []
    cursor: str | None = None
    pages = 0
    while pages < max_pages:
        query = dict(params)
        if cursor:
            query["cursor"] = cursor
        resp = httpx.get(
            f"{_api_root()}{path}",
            headers=_headers(),
            params=query,
            timeout=_timeout(quick=quick),
        )
        resp.raise_for_status()
        payload = resp.json()
        items.extend(payload.get("items", []))
        cursor = payload.get("nextCursor")
        pages += 1
        if not cursor:
            break
    return items


def _transcript_for_conversation(conv: dict) -> str:
    content = (conv.get("content") or "").strip()
    if content:
        return content

    summary = (conv.get("summary") or "").strip()
    if summary:
        return summary

    start = conv.get("startTime")
    end = conv.get("endTime")
    if not start or not end:
        return _fallback_transcript(conv)

    try:
        segments = _get_paginated(
            "/transcriptions",
            {"startTime": start, "endTime": end},
            max_pages=5,
        )
    except httpx.HTTPError:
        return _fallback_transcript(conv)

    if not segments:
        return _fallback_transcript(conv)

    lines: list[str] = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        speaker = (seg.get("speaker") or "").strip()
        lines.append(f"{speaker}: {text}" if speaker else text)
    transcript = "\n".join(lines)
    return transcript or _fallback_transcript(conv)


def fetch_conversations(
    start: date | None = None,
    end: date | None = None,
    *,
    include_transcripts: bool = True,
) -> list[dict]:
    """
    Conversations shaped for fieldy_ingest.ingest_conversations:
    id, title, date, transcript, speaker_me.

    Set include_transcripts=False for cockpit reads (one list call; titles only).
    """
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    end = end or date.today()
    start = start or (end - timedelta(days=1))
    speaker_me = os.getenv("FIELDY_SPEAKER_ME", "Lindsey")

    raw = _get_paginated(
        "/conversations",
        _range_params(start, end),
        quick=not include_transcripts,
    )

    convos: list[dict] = []
    for c in raw:
        start_time = c.get("startTime") or ""
        if include_transcripts:
            try:
                transcript = _transcript_for_conversation(c)
            except Exception:
                transcript = _fallback_transcript(c)
        else:
            transcript = _fallback_transcript(c)
        convos.append(
            {
                "id": c.get("id"),
                "title": c.get("title") or c.get("name", ""),
                "date": start_time[:10] if start_time else "",
                "transcript": transcript,
                "my_utterances": c.get("my_utterances"),
                "speaker_me": c.get("speaker_me") or speaker_me,
            }
        )
    return convos


def fetch_yesterday(*, include_transcripts: bool = True) -> list[dict]:
    yesterday = date.today() - timedelta(days=1)
    return fetch_conversations(
        start=yesterday,
        end=yesterday,
        include_transcripts=include_transcripts,
    )


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
