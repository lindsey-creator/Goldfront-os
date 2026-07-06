"""Apple Health connector — reads a local export file (read-only display)."""

from __future__ import annotations

import json
from pathlib import Path

from brain.connectors.base import ConnectorNotConfigured, env_optional, is_configured

CONNECTOR = "apple_health"
ENV_VARS = ["APPLE_HEALTH_EXPORT_PATH"]


def configured() -> bool:
    return is_configured(*ENV_VARS)


def fetch_metrics() -> dict:
    """
    Read metrics from a JSON export the user syncs to disk.
    No cloud API — display only.
    """
    path_str = env_optional("APPLE_HEALTH_EXPORT_PATH")
    if not path_str:
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    path = Path(path_str)
    if not path.is_file():
        raise ConnectorNotConfigured(
            CONNECTOR,
            [f"APPLE_HEALTH_EXPORT_PATH (file not found: {path})"],
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "recovery": data.get("recovery"),
        "hrv": data.get("hrv"),
        "sleep_hours": data.get("sleep_hours") or data.get("sleep"),
        "strain": data.get("strain") or data.get("active_energy"),
        "resting_hr": data.get("resting_hr") or data.get("resting_heart_rate"),
        "source": "apple_health",
        "note": "Display only — not medical advice.",
    }
