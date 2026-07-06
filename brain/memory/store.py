"""
Storage backend for the Brain's memory (master spec §5.2).

Two backends behind one interface:
  • ChromaVectorStore — real vector memory, used when `chromadb` is installed.
  • JsonVectorStore   — dependency-free fallback (keyword scoring). Lets the whole
                        training loop run — and be tested — with no ChromaDB and
                        no API keys. Cowork swaps to Chroma by just installing it.

`get_store()` picks the best available backend automatically. Both backends store
the same records: {id, text, metadata} and support add / query / all / count.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Iterable


def _new_id() -> str:
    return uuid.uuid4().hex


class BaseVectorStore:
    """Interface both backends implement."""

    def add(self, collection: str, text: str, metadata: dict | None = None) -> str:
        raise NotImplementedError

    def query(self, collection: str, text: str, n: int = 5) -> list[dict]:
        raise NotImplementedError

    def all(self, collection: str) -> list[dict]:
        raise NotImplementedError

    def count(self, collection: str) -> int:
        return len(self.all(collection))


# ---------------------------------------------------------------------------
# JSON fallback backend
# ---------------------------------------------------------------------------
_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall((text or "").lower()))


class JsonVectorStore(BaseVectorStore):
    """
    File-backed store. One JSON file per collection under `path`. Query uses
    Jaccard token overlap — good enough for tests and small local corpora, and
    it means the system is never blocked on an embedding service.
    """

    def __init__(self, path: str = "./.memory"):
        self.root = Path(path)
        self.root.mkdir(parents=True, exist_ok=True)

    def _file(self, collection: str) -> Path:
        return self.root / f"{collection}.json"

    def _load(self, collection: str) -> list[dict]:
        f = self._file(collection)
        if not f.exists():
            return []
        try:
            return json.loads(f.read_text() or "[]")
        except json.JSONDecodeError:
            return []

    def _save(self, collection: str, rows: list[dict]) -> None:
        self._file(collection).write_text(json.dumps(rows, indent=2))

    def add(self, collection: str, text: str, metadata: dict | None = None) -> str:
        rows = self._load(collection)
        rid = _new_id()
        rows.append(
            {
                "id": rid,
                "text": text,
                "metadata": metadata or {},
                "_ts": time.time(),
            }
        )
        self._save(collection, rows)
        return rid

    def query(self, collection: str, text: str, n: int = 5) -> list[dict]:
        q = _tokens(text)
        rows = self._load(collection)
        if not q:
            return rows[:n]
        scored = []
        for r in rows:
            t = _tokens(r.get("text", ""))
            overlap = len(q & t)
            if overlap:
                score = overlap / len(q | t)
                scored.append((score, r))
        scored.sort(key=lambda s: s[0], reverse=True)
        return [r for _, r in scored[:n]]

    def all(self, collection: str) -> list[dict]:
        return self._load(collection)


# ---------------------------------------------------------------------------
# ChromaDB backend
# ---------------------------------------------------------------------------
class ChromaVectorStore(BaseVectorStore):
    """Real vector memory. Used automatically when chromadb imports cleanly."""

    def __init__(self, path: str = "./.chroma"):
        import chromadb  # noqa: F401 (import guarded by get_store)

        self._client = chromadb.PersistentClient(path=path)

    def _col(self, collection: str):
        return self._client.get_or_create_collection(collection)

    def add(self, collection: str, text: str, metadata: dict | None = None) -> str:
        rid = _new_id()
        # Chroma metadata values must be primitives; JSON-encode nested bits.
        clean = {
            k: (v if isinstance(v, (str, int, float, bool)) else json.dumps(v))
            for k, v in (metadata or {}).items()
        }
        clean.setdefault("_ts", time.time())
        self._col(collection).add(ids=[rid], documents=[text], metadatas=[clean])
        return rid

    def query(self, collection: str, text: str, n: int = 5) -> list[dict]:
        res = self._col(collection).query(query_texts=[text], n_results=n)
        out = []
        ids = (res.get("ids") or [[]])[0]
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        for i, rid in enumerate(ids):
            out.append({"id": rid, "text": docs[i], "metadata": metas[i]})
        return out

    def all(self, collection: str) -> list[dict]:
        res = self._col(collection).get()
        out = []
        for i, rid in enumerate(res.get("ids", [])):
            out.append(
                {
                    "id": rid,
                    "text": res["documents"][i],
                    "metadata": res["metadatas"][i],
                }
            )
        return out


# ---------------------------------------------------------------------------
# Backend selection
# ---------------------------------------------------------------------------
def get_store(path: str | None = None, workspace: str | None = None) -> BaseVectorStore:
    """
    Return the best available backend, namespaced by `workspace`.

    Each workspace (owner id, e.g. "lindsey", "ryan-arth", or "goldfront-shared")
    gets its OWN physical directory, so brains never see each other's data. Two
    stores under the same base with different workspaces are fully isolated.

    Force the fallback with GOLDFRONT_MEMORY_BACKEND=json (used by tests).
    """
    ws = workspace or ""

    def _p(default: str) -> str:
        base = path or default
        return os.path.join(base, ws) if ws else base

    backend = os.getenv("GOLDFRONT_MEMORY_BACKEND", "auto").lower()
    if backend == "json":
        return JsonVectorStore(_p("./.memory"))
    if backend in ("chroma", "auto"):
        try:
            return ChromaVectorStore(_p("./.chroma"))
        except Exception:
            if backend == "chroma":
                raise
            return JsonVectorStore(_p("./.memory"))
    return JsonVectorStore(_p("./.memory"))
