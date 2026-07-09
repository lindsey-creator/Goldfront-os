"""In-memory approval queue — human gate before tasks or drafts leave (master spec §3.3)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from threading import Lock

from brain.connectors import clickup

_store: dict[str, dict] = {}
_lock = Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def enqueue(kind: str, content: str, meta: dict | None = None) -> str:
    aid = str(uuid.uuid4())
    with _lock:
        _store[aid] = {
            "id": aid,
            "kind": kind,
            "content": content,
            "meta": meta or {},
            "status": "pending",
            "created_at": _now(),
        }
    return aid


def get(aid: str) -> dict | None:
    with _lock:
        item = _store.get(aid)
        return dict(item) if item else None


def pending() -> list[dict]:
    with _lock:
        return [dict(v) for v in _store.values() if v["status"] == "pending"]


def approve(aid: str, content: str | None = None) -> dict:
    with _lock:
        item = _store.get(aid)
        if not item:
            return {"status": "error", "error": "Approval not found"}
        if item["status"] != "pending":
            return {"status": "error", "error": f"Already {item['status']}"}

        text = (content or item["content"] or "").strip()
        if item["kind"] == "task":
            if not clickup.configured():
                return {"status": "connect_source", "sources": ["clickup"]}
            try:
                created = clickup.create_task(
                    text,
                    assignee_hint=item["meta"].get("assignee_hint"),
                )
            except Exception as e:
                return {"status": "error", "error": str(e)}
            item["status"] = "approved"
            item["resolved_at"] = _now()
            return {
                "status": "ok",
                "kind": "task",
                "task_id": created.get("id"),
                "url": created.get("url"),
                "note": "Created in ClickUp.",
            }

        item["content"] = text
        item["status"] = "approved"
        item["resolved_at"] = _now()
        return {
            "status": "ok",
            "kind": "draft",
            "content": text,
            "note": "Draft approved — nothing sends automatically.",
        }


def deny(aid: str) -> dict:
    with _lock:
        item = _store.get(aid)
        if not item:
            return {"status": "error", "error": "Approval not found"}
        if item["status"] != "pending":
            return {"status": "error", "error": f"Already {item['status']}"}
        item["status"] = "denied"
        item["resolved_at"] = _now()
        return {"status": "ok", "kind": item["kind"]}
