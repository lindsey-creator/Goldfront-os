"""Runtime loader for OPERATING_BRAIN.md — single source of truth for Echo."""

from __future__ import annotations

from pathlib import Path

_OPERATING_BRAIN_PATH = Path(__file__).resolve().parent / "OPERATING_BRAIN.md"
_cached: str | None = None


def operating_brain_path() -> Path:
    return _OPERATING_BRAIN_PATH


def operating_brain_loaded() -> bool:
    return _OPERATING_BRAIN_PATH.is_file()


def load_operating_brain(*, refresh: bool = False) -> str:
    """Return the full OPERATING_BRAIN.md text. Cached after first read."""
    global _cached
    if refresh or _cached is None:
        if not operating_brain_loaded():
            return ""
        _cached = _OPERATING_BRAIN_PATH.read_text(encoding="utf-8")
    return _cached
