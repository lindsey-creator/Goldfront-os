"""
Memory / knowledge base (master spec §5.2).

Four collections hold your judgment:
    knowledge              your rules, playbooks, pricing logic, Baker's checklist
    voice                  examples of how you write/speak, for drafting
    decisions              GO/NO-GO/CONDITIONAL calls + reasoning, recency-weighted
    conversation_patterns  full outreach threads: how you qualify, object, close

Recency weighting uses config.DECISION_HALFLIFE_DAYS (180-day half-life): recent
calls dominate old ones (§3.5).
"""

from __future__ import annotations

import time

from brain.config import DECISION_HALFLIFE_DAYS, OWNER, SHARED_WORKSPACE
from brain.memory.store import BaseVectorStore, get_store

COLLECTIONS = ("knowledge", "voice", "decisions", "conversation_patterns")


class KnowledgeBase:
    """
    One person's private brain. `workspace` isolates it from every other brain —
    defaults to config.OWNER (whose instance this is). Use `KnowledgeBase.shared()`
    for the partnership-common Goldfront knowledge everyone opts into.
    """

    def __init__(
        self,
        store: BaseVectorStore | None = None,
        path: str | None = None,
        workspace: str | None = None,
    ):
        self.workspace = workspace or OWNER
        self.store = store or get_store(path, workspace=self.workspace)

    @classmethod
    def shared(cls, path: str | None = None) -> "KnowledgeBase":
        """The Goldfront shared brain — partnership-common rules/pipeline."""
        return cls(path=path, workspace=SHARED_WORKSPACE)

    # -- generic ------------------------------------------------------------
    def add(self, collection: str, text: str, metadata: dict | None = None) -> str:
        if collection not in COLLECTIONS:
            raise ValueError(f"Unknown collection {collection!r}. One of {COLLECTIONS}.")
        return self.store.add(collection, text, metadata)

    def query(self, collection: str, text: str, n: int = 5) -> list[dict]:
        return self.store.query(collection, text, n)

    def count(self, collection: str) -> int:
        return self.store.count(collection)

    # -- typed helpers the training layer uses ------------------------------
    def add_voice(self, text: str, recipient: str, context: str, meta: dict | None = None) -> str:
        m = {"recipient": recipient, "context": context, "kind": "voice"}
        if meta:
            m.update(meta)
        return self.add("voice", text, m)

    def add_decision(self, text: str, metadata: dict) -> str:
        m = {"kind": "decision", "_ts": time.time(), **metadata}
        return self.add("decisions", text, m)

    def add_team_interaction(self, text: str, category: str, person: str, meta: dict | None = None) -> str:
        # team interactions inform drafting/advice -> stored in voice with a category
        m = {"kind": "team_interaction", "category": category, "person": person}
        if meta:
            m.update(meta)
        return self.add("voice", text, m)

    def add_conversation(self, text: str, metadata: dict | None = None) -> str:
        m = {"kind": "conversation", **(metadata or {})}
        return self.add("conversation_patterns", text, m)

    # -- recency-weighted decision history ----------------------------------
    def recency_weight(self, age_days: float) -> float:
        """0.5 ** (age_days / half-life). Recent decisions dominate."""
        return 0.5 ** (age_days / DECISION_HALFLIFE_DAYS)

    def decisions_history(self, verdict: str | None = None, limit: int | None = None) -> list[dict]:
        """
        All trained decisions, newest first, optionally filtered by verdict
        (GO / NO-GO / CONDITIONAL). Each row carries a `recency_weight` so the
        agent can lean on recent calls.
        """
        rows = self.store.all("decisions")
        now = time.time()
        for r in rows:
            ts = r.get("metadata", {}).get("_ts") or r.get("_ts") or now
            age_days = max(0.0, (now - float(ts)) / 86400.0)
            r["age_days"] = round(age_days, 2)
            r["recency_weight"] = round(self.recency_weight(age_days), 4)
        rows.sort(key=lambda r: r.get("metadata", {}).get("_ts", r.get("_ts", 0)), reverse=True)
        if verdict:
            v = verdict.upper()
            rows = [r for r in rows if r.get("metadata", {}).get("verdict", "").upper() == v]
        if limit:
            rows = rows[:limit]
        return rows
