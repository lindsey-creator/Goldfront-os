"""Connector configuration status — never exposes secret values."""

from __future__ import annotations

from brain.connectors import apple_health, clickup, fieldy, gcal, ghl, gmail, whoop


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
        connectors[name] = {
            "connected": connected,
            "env_vars": env_vars,
        }
    connected_count = sum(1 for c in connectors.values() if c["connected"])
    return {
        "connectors": connectors,
        "connected_count": connected_count,
        "total": len(connectors),
    }
