"""
Memory / knowledge base (master spec §5.2).

Wraps ChromaDB with the four collections that hold your judgment:
    knowledge              your rules, playbooks, pricing logic, Baker's checklist
    voice                  examples of how you write/speak, for drafting
    decisions              GO/NO-GO/CONDITIONAL calls + reasoning, recency-weighted
    conversation_patterns  full outreach threads: how you qualify, object, close

STUB: interface is defined; implementation is a Cowork build step (sequence §2).
Recency weighting uses config.DECISION_HALFLIFE_DAYS (180-day half-life).
"""

from brain.config import DECISION_HALFLIFE_DAYS

COLLECTIONS = ("knowledge", "voice", "decisions", "conversation_patterns")


class KnowledgeBase:
    def __init__(self, db_path: str = "./.chroma"):
        self.db_path = db_path
        # TODO(cowork): init chromadb.PersistentClient + get_or_create each collection
        raise NotImplementedError("Build in Cowork — see master-spec §5.2")

    def add(self, collection: str, text: str, metadata: dict | None = None): ...
    def query(self, collection: str, text: str, n: int = 5): ...
    def recency_weight(self, age_days: float) -> float:
        """0.5 ** (age_days / half-life). Recent decisions dominate."""
        return 0.5 ** (age_days / DECISION_HALFLIFE_DAYS)
