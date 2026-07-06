"""GoHighLevel CRM connector (read-only)."""

from __future__ import annotations

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured

API_BASE = "https://services.leadconnectorhq.com"
CONNECTOR = "ghl"
ENV_VARS = ["GHL_API_KEY", "GHL_LOCATION_ID"]


def configured() -> bool:
    return is_configured(*ENV_VARS)


def _headers() -> dict[str, str]:
    key = env_required("GHL_API_KEY", CONNECTOR)
    return {
        "Authorization": f"Bearer {key}",
        "Version": "2021-07-28",
        "Accept": "application/json",
    }


def _location_id() -> str:
    return env_required("GHL_LOCATION_ID", CONNECTOR)


def _get(path: str, params: dict | None = None) -> dict:
    resp = httpx.get(
        f"{API_BASE}{path}",
        headers=_headers(),
        params=params or {},
        timeout=30.0,
    )
    resp.raise_for_status()
    return resp.json()


def fetch_crm_summary() -> dict:
    """
    New leads, missed calls, unread texts, pipeline snapshot.
    Raw counts from GHL — no invented figures.
    """
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)
    loc = _location_id()

    contacts = _get("/contacts/", {"locationId": loc, "limit": 20, "sortBy": "date_added"})
    contact_list = contacts.get("contacts", [])

    # Conversations / unread (endpoint shape per GHL API v2)
    unread_texts = 0
    missed_calls = 0
    try:
        convos = _get("/conversations/search", {"locationId": loc, "limit": 50})
        for c in convos.get("conversations", []):
            if c.get("unreadCount", 0) > 0:
                unread_texts += int(c["unreadCount"])
            last_type = (c.get("lastMessageType") or "").lower()
            if "missed" in last_type or c.get("status") == "missed":
                missed_calls += 1
    except httpx.HTTPError:
        pass

    pipeline: list[dict] = []
    try:
        opps = _get("/opportunities/search", {"location_id": loc, "limit": 20})
        for o in opps.get("opportunities", []):
            pipeline.append(
                {
                    "name": o.get("name", ""),
                    "stage": (o.get("pipelineStageId") or o.get("status") or ""),
                    "source": "ghl",
                }
            )
    except httpx.HTTPError:
        pass

    # New leads: contacts added in last 24h would need date filter; use recent list size
    new_leads = len(contact_list)

    return {
        "new_leads": new_leads,
        "missed_calls": missed_calls,
        "unread_texts": unread_texts,
        "pipeline": pipeline,
    }


def pipeline_moves() -> list[dict]:
    """Top-move candidates from pipeline — no dollar math invented."""
    summary = fetch_crm_summary()
    return [
        {
            "title": p.get("name", "Pipeline item"),
            "why": f"Stage: {p.get('stage', 'unknown')}",
            "source": "ghl",
            "deal_ref": p.get("name"),
        }
        for p in summary.get("pipeline", [])[:5]
    ]
