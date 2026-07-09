"""Meta Ads read-only connector (spend, leads, CPL)."""

from __future__ import annotations

from datetime import date, timedelta

import httpx

from brain.connectors.base import ConnectorNotConfigured, env_required, is_configured

API_BASE = "https://graph.facebook.com/v21.0"
CONNECTOR = "meta"
ENV_VARS = ["META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"]


def configured() -> bool:
    return is_configured(*ENV_VARS)


def _token() -> str:
    return env_required("META_ACCESS_TOKEN", CONNECTOR)


def _account_id() -> str:
    raw = env_required("META_AD_ACCOUNT_ID", CONNECTOR)
    return raw if raw.startswith("act_") else f"act_{raw}"


def fetch_ads_summary() -> dict:
    """Daily spend, leads, cost per lead from Meta Marketing API."""
    if not configured():
        raise ConnectorNotConfigured(CONNECTOR, ENV_VARS)

    since = (date.today() - timedelta(days=1)).isoformat()
    until = date.today().isoformat()
    params = {
        "access_token": _token(),
        "fields": "spend,impressions,clicks,actions,cost_per_action_type",
        "time_range": f'{{"since":"{since}","until":"{until}"}}',
        "level": "account",
    }
    resp = httpx.get(
        f"{API_BASE}/{_account_id()}/insights",
        params=params,
        timeout=30.0,
    )
    resp.raise_for_status()
    rows = resp.json().get("data", [])
    if not rows:
        return {"daily_spend": 0, "leads": 0, "cost_per_lead": None}

    row = rows[0]
    spend = float(row.get("spend") or 0)
    leads = 0
    for action in row.get("actions") or []:
        if action.get("action_type") in ("lead", "onsite_conversion.lead_grouped"):
            leads += int(float(action.get("value") or 0))
    cpl = round(spend / leads, 2) if leads > 0 else None
    return {
        "daily_spend": round(spend, 2),
        "leads": leads,
        "cost_per_lead": cpl,
    }
