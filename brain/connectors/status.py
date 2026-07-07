"""Connector configuration status — never exposes secret values."""

from __future__ import annotations

import os

from brain.connectors import apple_health, clickup, fieldy, gcal, ghl, gmail, whoop

GHL_TEAM_LOCATION_ID = "FFdZCVGXSQQThtHZEOYx"


def connectors_status() -> dict:
    entries = [
        ("clickup", clickup.ENV_VARS, clickup.configured()),
        ("fieldy", fieldy.ENV_VARS, fieldy.configured()),
        ("google_calendar", gcal.ENV_VARS, gcal.configured()),
        ("gmail", gmail.ENV_VARS, gmail.configured()),
        ("ghl", ghl.ENV_VARS, ghl.configured()),
        ("whoop", whoop.ENV_VARS, whoop.configured()),
        ("apple_health", apple_health.ENV_VARS, apple_health.configured()),
    ]
    connectors = {}
    for name, env_vars, connected in entries:
        info: dict = {
            "connected": connected,
            "env_vars": env_vars,
        }
        if name == "ghl" and connected:
            loc = (os.getenv("GHL_LOCATION_ID") or "").strip()
            if loc:
                info["active_location_id"] = loc
                info["team_location_id"] = GHL_TEAM_LOCATION_ID
                if loc == GHL_TEAM_LOCATION_ID:
                    info["location_label"] = "Team (The Conrad Team)"
                else:
                    info["location_label"] = "Personal sub-account"
                    info["location_note"] = (
                        "Operating doc uses team location "
                        f"{GHL_TEAM_LOCATION_ID}. Set GHL_LOCATION_ID to that ID "
                        "in goldfront-os/.env to read team CRM."
                    )
        connectors[name] = info
    connected_count = sum(1 for c in connectors.values() if c["connected"])
    return {
        "connectors": connectors,
        "connected_count": connected_count,
        "total": len(connectors),
    }
