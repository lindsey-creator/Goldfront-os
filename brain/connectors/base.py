"""Shared connector utilities."""

from __future__ import annotations

import os
from typing import Callable, TypeVar

T = TypeVar("T")


class ConnectorNotConfigured(Exception):
    """Raised when required env vars for a connector are missing."""

    def __init__(self, connector: str, env_vars: list[str]):
        self.connector = connector
        self.env_vars = env_vars
        super().__init__(
            f"{connector} not configured — set: {', '.join(env_vars)}"
        )


def env_required(name: str, connector: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConnectorNotConfigured(connector, [name])
    return value


def env_optional(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def is_configured(*env_names: str) -> bool:
    return all(os.getenv(n, "").strip() for n in env_names)


def safe_fetch(connector: str, env_vars: list[str], fn: Callable[[], T]) -> T | None:
    """Call fn when configured; return None when not (cockpit fallback)."""
    if not is_configured(*env_vars):
        return None
    try:
        return fn()
    except ConnectorNotConfigured:
        return None


def section_ok(items: list, source: str) -> dict:
    return {"status": "ok", "sources": [source], "items": items}


def section_needs(*sources: str) -> dict:
    return {"status": "connect_source", "sources": list(sources), "items": []}
