"""Google Calendar connector (read-only)."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import httpx

from brain.connectors.base import ConnectorNotConfigured
from brain.connectors.google_auth import google_headers, is_google_configured

CONNECTOR = "google_calendar"
ENV_VARS = ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN"]

PROTECTED_KEYWORDS = (
    "training",
    "recovery",
    "family",
    "workout",
    "gym",
    "rest",
    "kids",
)


def configured() -> bool:
    return is_google_configured()


def _calendar_id() -> str:
    return os.getenv("GOOGLE_CALENDAR_ID", "primary")


def _fetch_events(time_min: datetime, time_max: datetime) -> list[dict]:
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    resp = httpx.get(
        "https://www.googleapis.com/calendar/v3/calendars/"
        f"{_calendar_id()}/events",
        headers=google_headers(),
        params={
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 50,
        },
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def _normalize_event(ev: dict) -> dict:
    start = ev.get("start", {})
    start_str = start.get("dateTime") or start.get("date") or ""
    title = ev.get("summary", "(no title)")
    lower = title.lower()
    protected = any(k in lower for k in PROTECTED_KEYWORDS)
    return {
        "title": title,
        "start": start_str,
        "end": (ev.get("end", {}).get("dateTime") or ev.get("end", {}).get("date")),
        "protected": protected,
        "source": "google_calendar",
    }


def fetch_today() -> list[dict]:
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    tz = timezone.utc
    today = date.today()
    start = datetime.combine(today, datetime.min.time(), tzinfo=tz)
    end = start + timedelta(days=1)
    return [_normalize_event(ev) for ev in _fetch_events(start, end)]


def fetch_week_ahead() -> list[dict]:
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    tz = timezone.utc
    today = date.today()
    start = datetime.combine(today, datetime.min.time(), tzinfo=tz)
    end = start + timedelta(days=7)
    return [_normalize_event(ev) for ev in _fetch_events(start, end)]


def protected_blocks() -> list[dict]:
    return [e for e in fetch_week_ahead() if e.get("protected")]
