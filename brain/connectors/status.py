"""Connector configuration status — never exposes secret values."""

from __future__ import annotations

import os

from brain.connectors import (
    apple_health,
    clickup,
    fieldy,
    gcal,
    ghl,
    gmail,
    meta,
    weather,
    whoop,
)
from brain.connectors.whoop_auth import setup_note as whoop_setup_note

GHL_TEAM_LOCATION_ID = "FFdZCVGXSQQThtHZEOYx"
# Personal sub-account used by rhinolending.capital/apply capture — not Brain CRM writes.
GHL_PERSONAL_APPLY_LOCATION_ID = "3nUeqiIgQEtLuQJUbWVO"


def connectors_status() -> dict:
    entries = [
        ("clickup", clickup.ENV_VARS, clickup.configured()),
        ("fieldy", fieldy.ENV_VARS, fieldy.configured()),
        ("google_calendar", gcal.ENV_VARS, gcal.configured()),
        ("gmail", gmail.ENV_VARS, gmail.configured()),
        ("ghl", ghl.ENV_VARS, ghl.configured()),
        ("whoop", whoop.ENV_VARS, whoop.configured()),
        ("apple_health", apple_health.ENV_VARS, apple_health.configured()),
        ("meta", meta.ENV_VARS, meta.configured()),
        ("weather", weather.ENV_VARS, weather.configured()),
    ]
    connectors = {}
    for name, env_vars, connected in entries:
        info: dict = {
            "connected": connected,
            "env_vars": env_vars,
        }
        if name == "whoop" and not connected:
            note = whoop_setup_note()
            if note:
                info["setup_note"] = note
        if name == "ghl" and connected:
            loc = (os.getenv("GHL_LOCATION_ID") or "").strip()
            info["team_location_id"] = GHL_TEAM_LOCATION_ID
            info["personal_apply_location_id"] = GHL_PERSONAL_APPLY_LOCATION_ID
            if loc:
                info["active_location_id"] = loc
                if loc == GHL_TEAM_LOCATION_ID:
                    info["location_label"] = "Team (The Conrad Team)"
                elif loc == GHL_PERSONAL_APPLY_LOCATION_ID:
                    info["location_label"] = "Personal (apply capture only)"
                    info["location_note"] = (
                        "This ID is for rhinolending.capital/apply lead capture. "
                        f"Set GHL_LOCATION_ID={GHL_TEAM_LOCATION_ID} for team CRM."
                    )
                else:
                    info["location_label"] = "Other sub-account"
                    info["location_note"] = (
                        f"Team CRM: {GHL_TEAM_LOCATION_ID}. "
                        f"Apply capture (do not use for Brain writes): "
                        f"{GHL_PERSONAL_APPLY_LOCATION_ID}."
                    )
        connectors[name] = info
    connected_count = sum(1 for c in connectors.values() if c["connected"])
    return {
        "connectors": connectors,
        "connected_count": connected_count,
        "total": len(connectors),
    }
