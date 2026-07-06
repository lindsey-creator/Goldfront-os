"""Route ClickUp records into the right Brain memory collection."""

from __future__ import annotations

import re

VERDICT_RE = re.compile(r"\b(GO|NO-GO|NO GO|CONDITIONAL)\b", re.I)
ADDRESS_RE = re.compile(
    r"(?:deal|property|address)[:\s]+([^\n|]+)|(\d+\s+[\w\s]+(?:st|street|ave|avenue|rd|road|dr|drive|ln|lane|blvd|way|ct|court)\b[^\n|]*)",
    re.I,
)

DECISION_HINTS = (
    "decision",
    "decisions",
    "deal",
    "deals",
    "pipeline",
    "buy box",
    "buybox",
    "verdict",
    "go/no",
    "underwrite",
    "underwriting",
)
VOICE_HINTS = ("template", "script", "voice", "outreach", "email", "message", "copy")
CONVERSATION_HINTS = ("conversation", "thread", "exchange", "call log", "outreach log")


def _hint_blob(record: dict) -> str:
    parts = [
        record.get("title") or "",
        record.get("text") or "",
        record.get("list_name") or "",
        record.get("folder_name") or "",
        record.get("space_name") or "",
        " ".join(record.get("tags") or []),
    ]
    return " ".join(parts).lower()


def route_collection(record: dict) -> str:
    """Pick knowledge | voice | decisions | conversation_patterns."""
    override = record.get("collection")
    if override in ("knowledge", "voice", "decisions", "conversation_patterns"):
        return override

    blob = _hint_blob(record)
    if any(h in blob for h in CONVERSATION_HINTS):
        return "conversation_patterns"
    if any(h in blob for h in VOICE_HINTS):
        return "voice"
    if any(h in blob for h in DECISION_HINTS) or VERDICT_RE.search(
        record.get("text") or ""
    ):
        return "decisions"
    return "knowledge"


def decision_metadata(record: dict) -> dict:
    """Best-effort metadata so decisions_history / money moves can use ClickUp imports."""
    title = (record.get("title") or "").strip()
    text = (record.get("text") or "").strip()
    combined = f"{title}\n{text}"
    verdict_match = VERDICT_RE.search(combined)
    verdict = (verdict_match.group(1) if verdict_match else "").upper().replace("NO GO", "NO-GO")
    address = title
    addr_match = ADDRESS_RE.search(combined)
    if addr_match:
        address = (addr_match.group(1) or addr_match.group(2) or title).strip()
    meta: dict = {
        "source": "clickup",
        "clickup_id": record.get("id"),
        "clickup_type": record.get("type"),
        "title": title or None,
        "url": record.get("url"),
    }
    if verdict:
        meta["verdict"] = verdict
    if address:
        meta["address"] = address
    reasoning = text if text and text != title else ""
    if reasoning:
        meta["reasoning"] = reasoning[:500]
    return {k: v for k, v in meta.items() if v is not None}
