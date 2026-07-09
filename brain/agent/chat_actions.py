"""Lightweight command parsing for Echo — sync ClickUp, complete tasks."""

from __future__ import annotations

import re

from brain.connectors import clickup
from brain.connectors.clickup_sync import maybe_sync

_SYNC_RE = re.compile(
    r"\b(?:sync|refresh|pull|update)\s+(?:click\s*up|clickup)\b",
    re.I,
)
_COMPLETE_RE = re.compile(
    r"\b(?:mark|complete|finish|close|done)\s+(?:task\s+)?([a-z0-9]{4,})\b",
    re.I,
)
_TASK_ID_RE = re.compile(r"\b(?:task\s+)?#?([a-z0-9]{6,})\b", re.I)


def try_chat_action(message: str) -> dict | None:
    """
    Run a deck action when the message matches a simple pattern.
    Returns a ChatResponse-shaped dict or None to fall through to reasoning.
    """
    text = (message or "").strip()
    if not text:
        return None

    if _SYNC_RE.search(text):
        if not clickup.configured():
            return {
                "answer": "ClickUp isn't connected — add API keys in Connections.",
                "action": "sync_clickup",
                "action_status": "connect_source",
                "mode": "action",
            }
        result = maybe_sync(force=True)
        if result is None:
            return {
                "answer": "ClickUp sync failed — connector not configured.",
                "action": "sync_clickup",
                "action_status": "connect_source",
                "mode": "action",
            }
        ingested = result.get("ingested", 0)
        fetched = result.get("records_fetched", "—")
        return {
            "answer": (
                f"ClickUp synced — {ingested} items ingested from {fetched} records."
            ),
            "action": "sync_clickup",
            "action_status": "ok",
            "action_result": result,
            "mode": "action",
        }

    task_id: str | None = None
    complete_match = _COMPLETE_RE.search(text)
    if complete_match:
        task_id = complete_match.group(1)
    elif re.search(r"\b(?:mark|complete|done)\b", text, re.I):
        id_match = _TASK_ID_RE.search(text)
        if id_match:
            task_id = id_match.group(1)

    if task_id:
        if not clickup.configured():
            return {
                "answer": "ClickUp isn't connected — can't complete tasks from here.",
                "action": "complete_task",
                "action_status": "connect_source",
                "mode": "action",
            }
        try:
            clickup.complete_task(task_id)
            return {
                "answer": f"Marked ClickUp task {task_id} done.",
                "action": "complete_task",
                "action_status": "ok",
                "action_result": {"task_id": task_id},
                "mode": "action",
            }
        except Exception as exc:
            return {
                "answer": f"Couldn't complete task {task_id}: {exc}",
                "action": "complete_task",
                "action_status": "error",
                "error": str(exc),
                "mode": "action",
            }

    return None
