"""ClickUp API v2 connector — full workspace read for Brain memory."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Any

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured
from brain.connectors.clickup_routing import (
    decision_metadata,
    route_collection,
    voice_transcript_metadata,
)

API_BASE = "https://api.clickup.com/api/v2"
CONNECTOR = "clickup"
ENV_VARS = ["CLICKUP_API_TOKEN", "CLICKUP_WORKSPACE_ID"]
MAX_TASK_PAGES = 20
MAX_COMMENT_TASKS = 150
TRANSCRIPT_CF_NAMES = ("summary", "transcript", "meeting notes", "brief", "recording notes")
TRANSCRIPT_PATH_HINTS = (
    "raw transcript",
    "meeting notes",
    "plaud",
    "fieldy",
    "voice memo",
    "processed brief",
)
TRANSCRIPT_NAME_RE = re.compile(
    r"^\d{2}-\d{2}\s|🎙️|plaud|fieldy|consultation:|recording|voice memo",
    re.I,
)
AUDIO_EXT_RE = re.compile(r"\.(mp3|m4a|wav|ogg|webm|aac|mpeg)(\?|$)", re.I)


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


def _custom_field_text(task: dict) -> str:
    parts: list[str] = []
    for cf in task.get("custom_fields") or []:
        name = (cf.get("name") or "").lower()
        if not any(h in name for h in TRANSCRIPT_CF_NAMES):
            continue
        val = cf.get("value")
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    return "\n\n".join(parts)


def _audio_attachment(task: dict) -> dict | None:
    for att in task.get("attachments") or []:
        ext = (att.get("extension") or att.get("mimetype") or att.get("title") or "").lower()
        if AUDIO_EXT_RE.search(ext) or any(
            x in ext for x in ("mp3", "m4a", "wav", "audio", "ogg", "webm", "aac")
        ):
            return att
    return None


def _task_body_text(task: dict) -> str:
    desc = (task.get("description") or "").strip()
    cf_text = _custom_field_text(task)
    if desc and cf_text and desc not in cf_text and cf_text not in desc:
        return f"{desc}\n\n{cf_text}"
    return desc or cf_text


def _is_transcript_task(task: dict) -> bool:
    ctx = _task_context(task)
    blob = " ".join(
        [
            task.get("name") or "",
            ctx["list_name"],
            ctx["folder_name"],
            ctx["space_name"],
            " ".join(ctx["tags"]),
        ]
    ).lower()
    if any(h in blob for h in TRANSCRIPT_PATH_HINTS):
        return True
    if TRANSCRIPT_NAME_RE.search(task.get("name") or ""):
        return True
    if "flagged from fieldy" in (task.get("description") or "").lower():
        return False
    return bool(_audio_attachment(task))


def _parse_task_date(task: dict) -> str:
    name = task.get("name") or ""
    m = re.search(r"\b(\d{2})-(\d{2})(?:\b|:)", name)
    if m:
        year = date.today().year
        created = task.get("date_created")
        if created:
            year = datetime.fromtimestamp(int(created) / 1000, tz=timezone.utc).year
        return f"{year}-{m.group(1)}-{m.group(2)}"
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", name)
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    created = task.get("date_created")
    if created:
        return datetime.fromtimestamp(int(created) / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d"
        )
    return ""


def _task_to_record(task: dict, *, text: str | None = None) -> dict:
    ctx = _task_context(task)
    body = (text or _task_body_text(task) or "").strip() or task.get("name", "")
    record = {
        "id": str(task.get("id", "")),
        "type": "task",
        "title": task.get("name"),
        "text": body,
        "url": task.get("url"),
        **ctx,
    }
    if _is_transcript_task(task):
        record["record_kind"] = "voice_transcript"
        record["record_date"] = _parse_task_date(task)
        att = _audio_attachment(task)
        if att:
            record["audio_attachment"] = att
        record["collection"] = "conversation_patterns"
    else:
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


def _transcript_convos_from_tasks(
    tasks: list[dict],
    *,
    days_back: int = 2,
    limit: int = 20,
) -> list[dict]:
    """Shape ClickUp transcript tasks like Fieldy conversations for the cockpit."""
    cutoff = date.today() - timedelta(days=days_back)
    convos: list[dict] = []
    for task in tasks:
        if not _is_transcript_task(task):
            continue
        text = _task_body_text(task).strip()
        if len(text) < 40:
            continue
        record_date = _parse_task_date(task)
        try:
            parsed = date.fromisoformat(record_date) if record_date else None
        except ValueError:
            parsed = None
        if parsed and parsed < cutoff:
            continue
        convos.append(
            {
                "id": str(task.get("id", "")),
                "title": task.get("name") or "Meeting transcript",
                "date": record_date,
                "transcript": text,
                "source": "clickup",
                "url": task.get("url"),
                "list_name": (task.get("list") or {}).get("name"),
            }
        )
    convos.sort(key=lambda c: c.get("date") or "", reverse=True)
    return convos[:limit]


def fetch_recent_transcripts(days_back: int = 2, limit: int = 20) -> list[dict]:
    """Recent meeting/audio transcripts synced into ClickUp (Plaud, Fieldy archive)."""
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    return _transcript_convos_from_tasks(
        fetch_tasks(include_closed=True),
        days_back=days_back,
        limit=limit,
    )


def fetch_fieldy_flagged_tasks(limit: int = 10) -> list[dict]:
    """Action items auto-created from Fieldy conversations — live in ClickUp."""
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    items: list[dict] = []
    for task in fetch_tasks(include_closed=False):
        desc = (task.get("description") or "").lower()
        if "flagged from fieldy" not in desc:
            continue
        items.append(
            {
                "title": (task.get("description") or task.get("name", ""))[:120],
                "detail": task.get("name", ""),
                "date": _parse_task_date(task),
                "source": "clickup",
                "url": task.get("url"),
            }
        )
    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    return items[:limit]


def commitments_from_transcripts(convos: list[dict]) -> list[dict]:
    """Best-effort commitment lines from ClickUp transcript summaries."""
    items: list[dict] = []
    for c in convos:
        text = c.get("transcript") or ""
        for line in text.splitlines():
            stripped = line.strip().lstrip("-•* ").strip()
            if not stripped or len(stripped) < 12:
                continue
            lower = stripped.lower()
            if any(
                kw in lower
                for kw in ("will ", "need to", "follow up", "reach out", "call ", "send ")
            ):
                items.append(
                    {
                        "title": stripped[:120],
                        "detail": c.get("title", ""),
                        "date": c.get("date"),
                        "source": c.get("source", "clickup"),
                    }
                )
    return items[:15]


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
    summary["transcripts_fetched"] = sum(
        1 for r in records if r.get("record_kind") == "voice_transcript"
    )
    return summary


def record_metadata(record: dict) -> dict:
    """Metadata stored with each ingested ClickUp item."""
    if record.get("record_kind") == "voice_transcript":
        return voice_transcript_metadata(record)
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
