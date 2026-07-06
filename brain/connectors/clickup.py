"""ClickUp API v2 connector — full workspace read for Brain memory."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured
from brain.connectors.clickup_routing import decision_metadata, route_collection

API_BASE = "https://api.clickup.com/api/v2"
CONNECTOR = "clickup"
ENV_VARS = ["CLICKUP_API_TOKEN", "CLICKUP_WORKSPACE_ID"]
MAX_TASK_PAGES = 20
MAX_COMMENT_TASKS = 150


def configured() -> bool:
    return is_configured(*ENV_VARS)


def _headers() -> dict[str, str]:
    token = env_required("CLICKUP_API_TOKEN", CONNECTOR)
    return {"Authorization": token}


def _team_id() -> str:
    return env_required("CLICKUP_WORKSPACE_ID", CONNECTOR)


def _get(path: str, params: dict | None = None) -> Any:
    url = f"{API_BASE}{path}"
    resp = httpx.get(url, headers=_headers(), params=params or {}, timeout=60.0)
    resp.raise_for_status()
    return resp.json()


def _task_context(task: dict) -> dict[str, str]:
    lst = task.get("list") or {}
    folder = task.get("folder") or {}
    space = task.get("space") or {}
    tags = [t.get("name", "") for t in (task.get("tags") or []) if t.get("name")]
    return {
        "list_name": lst.get("name") or "",
        "folder_name": folder.get("name") or "",
        "space_name": space.get("name") or "",
        "tags": tags,
    }


def _task_to_record(task: dict, *, text: str | None = None) -> dict:
    ctx = _task_context(task)
    body = (text or task.get("description") or "").strip() or task.get("name", "")
    record = {
        "id": str(task.get("id", "")),
        "type": "task",
        "title": task.get("name"),
        "text": body,
        "url": task.get("url"),
        **ctx,
    }
    record["collection"] = route_collection(record)
    return record


def fetch_tasks(include_closed: bool = True) -> list[dict]:
    """All workspace tasks (paginated)."""
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    all_tasks: list[dict] = []
    for page in range(MAX_TASK_PAGES):
        data = _get(
            f"/team/{_team_id()}/task",
            {
                "include_closed": str(include_closed).lower(),
                "page": page,
                "subtasks": "true",
            },
        )
        batch = data.get("tasks", [])
        if not batch:
            break
        all_tasks.extend(batch)
    return all_tasks


def fetch_task_comments(task_id: str) -> list[dict]:
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    return _get(f"/task/{task_id}/comment").get("comments", [])


def fetch_records() -> list[dict]:
    """
    Full workspace pull: tasks, comments, doc pages — routed for Brain memory.
    """
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)

    records: list[dict] = []
    seen: set[str] = set()

    def add(record: dict) -> None:
        rid = str(record.get("id") or "")
        if not rid or rid in seen:
            return
        text = (record.get("text") or "").strip()
        if not text:
            return
        seen.add(rid)
        if "collection" not in record:
            record["collection"] = route_collection(record)
        records.append(record)

    tasks = fetch_tasks(include_closed=True)
    comment_budget = MAX_COMMENT_TASKS
    for task in tasks:
        add(_task_to_record(task))
        if comment_budget <= 0:
            continue
        task_id = task.get("id")
        if not task_id:
            continue
        try:
            for comment in fetch_task_comments(str(task_id)):
                comment_budget -= 1
                text = (comment.get("comment_text") or "").strip()
                if not text:
                    continue
                ctx = _task_context(task)
                c_record = {
                    "id": f"{task_id}-c-{comment.get('id', comment_budget)}",
                    "type": "comment",
                    "title": task.get("name"),
                    "text": text,
                    "url": task.get("url"),
                    **ctx,
                }
                add(c_record)
                if comment_budget <= 0:
                    break
        except httpx.HTTPError:
            continue

    try:
        spaces = _get(f"/team/{_team_id()}/space").get("spaces", [])
        for space in spaces:
            space_name = space.get("name") or ""
            for doc in _get(f"/space/{space['id']}/doc").get("docs", []):
                doc_id = doc.get("id")
                if not doc_id:
                    continue
                try:
                    pages = _get(f"/doc/{doc_id}/page").get("pages", [])
                except httpx.HTTPError:
                    continue
                for page in pages:
                    content = (page.get("content") or page.get("name") or "").strip()
                    if not content:
                        continue
                    d_record = {
                        "id": str(page.get("id", doc_id)),
                        "type": "doc",
                        "title": page.get("name") or doc.get("name"),
                        "text": content,
                        "url": doc.get("url"),
                        "space_name": space_name,
                        "list_name": "",
                        "folder_name": "",
                        "tags": [],
                    }
                    add(d_record)
    except httpx.HTTPError:
        pass

    return records


def overdue_tasks() -> list[dict]:
    """Team Pulse shape: {person, task, due, days_late}."""
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    now = datetime.now(timezone.utc)
    overdue: list[dict] = []
    for task in fetch_tasks(include_closed=False):
        status = (task.get("status") or {}).get("status", "").lower()
        if status in ("complete", "closed", "done"):
            continue
        due_ms = task.get("due_date")
        if not due_ms:
            continue
        due = datetime.fromtimestamp(int(due_ms) / 1000, tz=timezone.utc)
        if due >= now:
            continue
        days_late = (now - due).days
        assignees = task.get("assignees") or []
        person = (
            assignees[0].get("username") or assignees[0].get("email") or "Unassigned"
            if assignees
            else "Unassigned"
        )
        overdue.append(
            {
                "person": person,
                "task": task.get("name", ""),
                "due": due.strftime("%Y-%m-%d"),
                "days_late": days_late,
            }
        )
    return sorted(overdue, key=lambda x: -x["days_late"])


def open_tasks(limit: int = 10) -> list[dict]:
    """Open tasks due soon — for watch list."""
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    now = datetime.now(timezone.utc)
    items: list[dict] = []
    for task in fetch_tasks(include_closed=False):
        status = (task.get("status") or {}).get("status", "").lower()
        if status in ("complete", "closed", "done"):
            continue
        due_ms = task.get("due_date")
        due_str = "no due date"
        sort_key = 9999
        if due_ms:
            due = datetime.fromtimestamp(int(due_ms) / 1000, tz=timezone.utc)
            if due < now:
                continue
            due_str = due.strftime("%Y-%m-%d")
            sort_key = (due - now).days
        assignees = task.get("assignees") or []
        person = (
            assignees[0].get("username") or assignees[0].get("email") or "Unassigned"
            if assignees
            else "Unassigned"
        )
        items.append(
            {
                "title": task.get("name", ""),
                "detail": f"{person} · due {due_str}",
                "source": "clickup",
                "_sort": sort_key,
            }
        )
    items.sort(key=lambda x: x["_sort"])
    for item in items:
        item.pop("_sort", None)
    return items[:limit]


def ingest_live(svc=None) -> dict:
    """Pull full ClickUp workspace into Brain memory."""
    from brain.training.importers import clickup_ingest

    records = fetch_records()
    summary = clickup_ingest.ingest_records(records, svc)
    summary["records_fetched"] = len(records)
    summary["tasks_fetched"] = sum(1 for r in records if r.get("type") == "task")
    return summary


def record_metadata(record: dict) -> dict:
    """Metadata stored with each ingested ClickUp item."""
    if record.get("collection") == "decisions":
        return decision_metadata(record)
    return {
        "source": "clickup",
        "clickup_id": record.get("id"),
        "clickup_type": record.get("type"),
        "title": record.get("title"),
        "url": record.get("url"),
        "list_name": record.get("list_name"),
    }
