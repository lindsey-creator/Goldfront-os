"""
ClickUp ingestion adapter (master spec §7 — ClickUp is live via MCP).

"ClickUp has all my brain stuff saved." This pulls that content into the Brain's
memory so the reasoning agent can draw on it.
"""

from __future__ import annotations

from typing import Callable

from brain.connectors.clickup_routing import route_collection
from brain.memory.knowledge_base import COLLECTIONS, KnowledgeBase
from brain.training.service import TrainingService

WORKSPACE_ID = "90141259054"  # master spec §7


def _existing_clickup_ids(kb: KnowledgeBase) -> set[tuple[str, str]]:
    """(collection, clickup_id) pairs already in memory — skip duplicates on re-sync."""
    seen: set[tuple[str, str]] = set()
    for collection in COLLECTIONS:
        for row in kb.store.all(collection):
            meta = row.get("metadata") or {}
            cid = meta.get("clickup_id")
            if cid:
                seen.add((collection, str(cid)))
    return seen


def _record_metadata(record: dict) -> dict:
    from brain.connectors.clickup import record_metadata

    return record_metadata(record)


def ingest_records(records: list[dict], svc: TrainingService | None = None) -> dict:
    svc = svc or TrainingService()
    seen = _existing_clickup_ids(svc.kb)
    added = {c: 0 for c in COLLECTIONS}
    skipped = 0
    duplicated = 0

    for r in records:
        text = (r.get("text") or "").strip()
        if not text:
            skipped += 1
            continue
        collection = route_collection(r)
        if collection not in COLLECTIONS:
            collection = "knowledge"
        cid = str(r.get("id") or "")
        if cid and (collection, cid) in seen:
            duplicated += 1
            continue

        meta = _record_metadata(r)
        title = r.get("title")
        body = f"{title}\n{text}" if title else text
        svc.kb.add(collection, body, meta)
        if cid:
            seen.add((collection, cid))
        added[collection] += 1

    return {
        "ingested": sum(added.values()),
        "by_collection": added,
        "skipped": skipped,
        "duplicated": duplicated,
    }


def fetch_and_ingest(fetcher: Callable[[], list[dict]], svc: TrainingService | None = None) -> dict:
    return ingest_records(fetcher(), svc)
