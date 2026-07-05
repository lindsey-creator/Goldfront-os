"""
ClickUp ingestion adapter (master spec §7 — ClickUp is live via MCP).

"ClickUp has all my brain stuff saved." This pulls that content into the Brain's
memory so the reasoning agent can draw on it.

Design note — how this runs:
  The live ClickUp data comes from the ClickUp MCP connector, which is only
  reachable inside an AUTHORIZED Cowork session (OAuth can't run in a headless
  build). So this adapter is split:

    • ingest_records(records, svc)  — pure, testable, no network. Routes already-
                                      fetched ClickUp items into the right memory
                                      collection.
    • fetch_and_ingest(fetcher, svc) — calls a `fetcher` you pass in. In Cowork you
                                      pass a fetcher that wraps the ClickUp MCP
                                      tools (clickup_get_workspace_hierarchy,
                                      clickup_get_document_pages, clickup_get_task,
                                      clickup_get_task_comments, ...). In tests we
                                      pass a fake fetcher returning sample records.

Record shape (what a fetcher must return): a list of dicts, each:
    {
      "id": "abc",                     # ClickUp id (task/doc/comment)
      "type": "task|doc|comment|list", # what it is
      "title": "…",                    # optional
      "text": "…",                     # the content to store (required)
      "url": "https://app.clickup.com/…",  # optional
      "collection": "knowledge",       # optional routing hint; default "knowledge"
    }

Routing default: everything lands in `knowledge` (your rules, playbooks, notes).
A record can override with "collection": one of knowledge|voice|decisions|
conversation_patterns.
"""

from __future__ import annotations

from typing import Callable

from brain.memory.knowledge_base import COLLECTIONS
from brain.training.service import TrainingService

WORKSPACE_ID = "90141259054"  # master spec §7


def ingest_records(records: list[dict], svc: TrainingService | None = None) -> dict:
    svc = svc or TrainingService()
    added = {c: 0 for c in COLLECTIONS}
    skipped = 0
    for r in records:
        text = (r.get("text") or "").strip()
        if not text:
            skipped += 1
            continue
        collection = r.get("collection", "knowledge")
        if collection not in COLLECTIONS:
            collection = "knowledge"
        meta = {
            "source": "clickup",
            "clickup_id": r.get("id"),
            "clickup_type": r.get("type"),
            "title": r.get("title"),
            "url": r.get("url"),
        }
        title = r.get("title")
        body = f"{title}\n{text}" if title else text
        svc.kb.add(collection, body, {k: v for k, v in meta.items() if v is not None})
        added[collection] += 1
    return {"ingested": sum(added.values()), "by_collection": added, "skipped": skipped}


def fetch_and_ingest(fetcher: Callable[[], list[dict]], svc: TrainingService | None = None) -> dict:
    """
    `fetcher` is a zero-arg callable returning records (see module docstring).
    Inside Cowork, wrap the ClickUp MCP tools; in tests, pass a fake.
    """
    return ingest_records(fetcher(), svc)
