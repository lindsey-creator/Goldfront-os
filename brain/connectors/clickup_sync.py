"""Throttled ClickUp → Brain memory sync."""

from __future__ import annotations

import os
import time
from typing import Any

from brain.connectors import clickup

_last_sync: float = 0.0
_last_result: dict[str, Any] | None = None
SYNC_INTERVAL_SEC = 15 * 60  # match Command Center refresh


def last_sync_result() -> dict[str, Any]:
    return {
        "configured": clickup.configured(),
        "auto_sync": os.getenv("CLICKUP_AUTO_SYNC", "true").lower() != "false",
        "last_sync_at": _last_sync or None,
        "last_result": _last_result,
    }


def maybe_sync(force: bool = False) -> dict[str, Any] | None:
    """
    Pull ClickUp into memory when configured. Throttled unless force=True.
    Returns ingest summary or skip reason; None when not configured.
    """
    global _last_sync, _last_result

    if not clickup.configured():
        return None
    if os.getenv("CLICKUP_AUTO_SYNC", "true").lower() == "false" and not force:
        return {"skipped": True, "reason": "auto_sync_disabled"}

    now = time.time()
    if not force and _last_sync and (now - _last_sync) < SYNC_INTERVAL_SEC:
        return {"skipped": True, "reason": "throttled", "last_sync_at": _last_sync}

    result = clickup.ingest_live()
    _last_sync = now
    _last_result = result
    result["synced_at"] = now
    return result
