"""Whoop recovery connector (read-only display)."""

from __future__ import annotations

import os
from datetime import date, timedelta

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured

API_BASE = "https://api.prod.whoop.com/developer/v2"
CONNECTOR = "whoop"
ENV_VARS = ["WHOOP_ACCESS_TOKEN"]


def configured() -> bool:
    return is_configured(*ENV_VARS)


def _headers() -> dict[str, str]:
    token = env_required("WHOOP_ACCESS_TOKEN", CONNECTOR)
    return {"Authorization": f"Bearer {token}"}


def fetch_recovery() -> dict:
    """
    Recovery, HRV, sleep, strain — display only, never prescribe.
  """
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    end = date.today()
    start = end - timedelta(days=7)
    resp = httpx.get(
        f"{API_BASE}/recovery",
        headers=_headers(),
        params={"start": start.isoformat(), "end": end.isoformat()},
        timeout=30.0,
    )
    resp.raise_for_status()
    records = resp.json().get("records", [])

    latest = records[-1] if records else {}
    score = latest.get("score", {})
    return {
        "recovery_score": score.get("recovery_score"),
        "hrv": score.get("hrv_rmssd_milli"),
        "resting_hr": score.get("resting_heart_rate"),
        "sleep_hours": (score.get("sleep") or {}).get("total_in_bed_time_milli"),
        "strain": latest.get("strain"),
        "source": "whoop",
        "note": "Display only — not medical advice.",
    }
