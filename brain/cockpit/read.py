"""
Cockpit read layer (master spec §6; command-center-experience.md).

Returns STABLE SHAPES for the Command Center. When a connector's env vars are
present, live data fills the module; otherwise `connect_source` — never fake data.
"""

from __future__ import annotations

from datetime import date, timedelta

from brain.connectors import (
    apple_health,
    clickup,
    fieldy,
    gcal,
    ghl,
    gmail,
    meta,
    weather,
    whoop,
)
from brain.connectors.base import ConnectorNotConfigured, section_needs, section_ok
from brain.connectors.clickup_sync import maybe_sync
from brain.memory.knowledge_base import KnowledgeBase


def _needs(source: str) -> dict:
    """Single optional source — never bundle multiple required connectors."""
    return section_needs(source)


def _merge_status(sections: list[dict]) -> str:
    statuses = {s.get("status") for s in sections}
    if statuses == {"connect_source"}:
        return "connect_source"
    if "ok" in statuses:
        return "ok" if "connect_source" not in statuses else "partial"
    return "connect_source"


class CockpitRead:
    def __init__(self, kb: KnowledgeBase | None = None):
        self.kb = kb or KnowledgeBase()

    def _ensure_clickup_sync(self) -> None:
        try:
            maybe_sync()
        except Exception:
            pass

    # -- helpers ------------------------------------------------------------
    def _clickup_overdue(self) -> list[dict] | None:
        if not clickup.configured():
            return None
        try:
            return clickup.overdue_tasks()
        except (ConnectorNotConfigured, Exception):
            return None

    def _fieldy_yesterday(self) -> list[dict] | None:
        if not fieldy.configured():
            return None
        try:
            return fieldy.fetch_yesterday(include_transcripts=False)
        except (ConnectorNotConfigured, Exception):
            return None

    def _clickup_transcripts(self, days_back: int = 2) -> list[dict] | None:
        if not clickup.configured():
            return None
        try:
            return clickup.fetch_recent_transcripts(days_back=days_back)
        except (ConnectorNotConfigured, Exception):
            return None

    def _voice_convos(self, days_back: int = 14) -> tuple[list[dict], str | None]:
        """Fieldy when it has data; otherwise ClickUp transcripts (Plaud/Fieldy archive)."""
        if fieldy.configured():
            try:
                end = date.today()
                start = end - timedelta(days=7)
                fieldy_convos = fieldy.fetch_conversations(
                    start=start,
                    end=end,
                    include_transcripts=False,
                )
                if fieldy_convos:
                    return fieldy_convos, "fieldy"
            except (ConnectorNotConfigured, Exception):
                pass
        if clickup.configured():
            try:
                return clickup.fetch_recent_transcripts(days_back=days_back), "clickup"
            except (ConnectorNotConfigured, Exception):
                pass
        if fieldy.configured():
            return [], "fieldy"
        if clickup.configured():
            return [], "clickup"
        return [], None

    def _calendar_today(self) -> list[dict] | None:
        if not gcal.configured():
            return None
        try:
            return gcal.fetch_today()
        except (ConnectorNotConfigured, Exception):
            return None

    def _calendar_week(self) -> list[dict] | None:
        if not gcal.configured():
            return None
        try:
            return gcal.fetch_week_ahead()
        except (ConnectorNotConfigured, Exception):
            return None

    def _ghl_summary(self) -> dict | None:
        if not ghl.configured():
            return None
        try:
            return ghl.fetch_crm_summary()
        except (ConnectorNotConfigured, Exception):
            return None

    # -- daily brief --------------------------------------------------------
    def daily_brief(self) -> dict:
        """
        Assembled morning brief:
        TODAY · WATCH LIST · ACCOUNTABILITY · COMMITMENTS I MADE · TOP 3 MONEY MOVES
        Plus legacy keys for the Command Center UI.
        """
        self._ensure_clickup_sync()
        sources: list[str] = []
        today_items: list[dict] = []
        watch_items: list[dict] = []
        accountability_items: list[dict] = []
        commitment_items: list[dict] = []
        money_items: list[dict] = []

        cal_today = self._calendar_today()
        if cal_today is not None:
            sources.append("google_calendar")
            today_items = cal_today
            for ev in cal_today:
                if ev.get("protected"):
                    watch_items.append(
                        {
                            "title": f"Protected: {ev['title']}",
                            "detail": ev.get("start", ""),
                            "source": "google_calendar",
                        }
                    )

        overdue = self._clickup_overdue()
        if overdue is not None:
            sources.append("clickup")
            for t in overdue:
                watch_items.append(
                    {
                        "title": t["task"],
                        "detail": f"{t['person']} · {t['days_late']}d late",
                        "source": "clickup",
                        "clickup_task_id": t.get("clickup_task_id"),
                    }
                )
                accountability_items.append(
                    {
                        "person": t["person"],
                        "committed": t["task"],
                        "actual": "overdue",
                        "suggested_move": f"Follow up — due {t['due']}",
                    }
                )

        fieldy_convos, voice_source = self._voice_convos()
        if voice_source:
            sources.append(voice_source)
            if voice_source == "fieldy":
                commitment_items = fieldy.commitments_from_convos(fieldy_convos)
            else:
                flagged = clickup.fetch_fieldy_flagged_tasks()
                commitment_items = flagged or clickup.commitments_from_transcripts(
                    fieldy_convos
                )
            for c in fieldy_convos[:5]:
                today_items.append(
                    {
                        "title": c.get("title") or "Meeting transcript",
                        "detail": (c.get("transcript") or "")[:200],
                        "date": c.get("date"),
                        "source": voice_source,
                    }
                )

        ghl_data = self._ghl_summary()
        if ghl_data is not None:
            sources.append("ghl")
            for move in ghl.pipeline_moves()[:3]:
                money_items.append(
                    {
                        "title": move["title"],
                        "dollars": None,
                        "why": move["why"],
                        "recommended_action": "Review pipeline stage",
                        "deal_ref": move.get("deal_ref"),
                    }
                )

        # Trained decisions inform moves — no invented dollar amounts
        for d in self.kb.decisions_history(limit=3):
            meta = d.get("metadata", {})
            money_items.append(
                {
                    "title": meta.get("address", "Trained decision"),
                    "dollars": None,
                    "why": meta.get("reasoning", "")[:200],
                    "recommended_action": f"Prior verdict: {meta.get('verdict')}",
                    "deal_ref": meta.get("address"),
                }
            )
        money_items = money_items[:3]

        money_sources: list[str] = []
        if ghl_data is not None:
            money_sources.append("ghl")
        if any(
            d.get("metadata", {}).get("address")
            for d in self.kb.decisions_history(limit=3)
        ):
            money_sources.append("brain_memory")

        today_sources: list[str] = []
        if cal_today is not None:
            today_sources.append("google_calendar")
        if voice_source:
            today_sources.append(voice_source)

        today_sec = (
            {"status": "ok", "sources": today_sources, "items": today_items}
            if today_items
            else _needs("google_calendar")
        )
        watch_sec = (
            section_ok(watch_items, "brain_scan")
            if watch_items
            else _needs("brain_scan")
        )
        accountability_sec = (
            {
                "status": "ok",
                "sources": ["clickup"],
                "items": accountability_items,
                "gaps": accountability_items,
            }
            if accountability_items
            else _needs("clickup")
        )
        commitments_sec = (
            section_ok(commitment_items, voice_source or "fieldy")
            if commitment_items
            else _needs(
                voice_source or ("clickup" if clickup.configured() else "fieldy")
            )
        )
        money_sec = (
            {
                "status": "ok",
                "sources": money_sources or ["brain_memory"],
                "items": money_items,
            }
            if money_items
            else _needs("ghl")
        )

        yesterday_iso = (date.today() - timedelta(days=1)).isoformat()
        yesterday_convos = [
            c for c in fieldy_convos if c.get("date") == yesterday_iso
        ] or fieldy_convos[:5]
        legacy_yesterday = (
            section_ok(
                [
                    {
                        "title": c.get("title", "Conversation"),
                        "detail": (c.get("transcript") or "")[:300],
                        "date": c.get("date"),
                        "source": voice_source or "fieldy",
                    }
                    for c in yesterday_convos
                ],
                voice_source or "fieldy",
            )
            if yesterday_convos and voice_source
            else _needs(
                voice_source or ("clickup" if clickup.configured() else "fieldy")
            )
        )
        legacy_schedule = (
            section_ok(cal_today or [], "google_calendar")
            if cal_today is not None
            else _needs("google_calendar")
        )
        legacy_owed = (
            section_ok(watch_items[:10], "clickup")
            if overdue is not None
            else _needs("clickup")
        )
        legacy_tasks = commitments_sec

        sections = [
            today_sec,
            watch_sec,
            accountability_sec,
            commitments_sec,
            money_sec,
        ]
        overall = _merge_status(sections)

        return {
            "status": overall,
            "sources": sorted(set(sources)),
            "today": today_sec,
            "watch_list": watch_sec,
            "accountability": accountability_sec,
            "commitments_i_made": commitments_sec,
            "top_money_moves": {**money_sec, "limit": 3},
            "yesterday": legacy_yesterday,
            "today_schedule": legacy_schedule,
            "commitments_owed": legacy_owed,
            "becomes_tasks": legacy_tasks,
        }

    def top_money_moves(self, limit: int = 3) -> dict:
        self._ensure_clickup_sync()
        moves: list[dict] = []
        sources: list[str] = []

        if ghl.configured():
            try:
                sources.append("ghl")
                for m in ghl.pipeline_moves()[:limit]:
                    moves.append(
                        {
                            "title": m["title"],
                            "dollars": None,
                            "why": m["why"],
                            "recommended_action": "Review in GHL",
                            "deal_ref": m.get("deal_ref"),
                        }
                    )
            except Exception:
                pass

        for d in self.kb.decisions_history(limit=limit):
            if len(moves) >= limit:
                break
            meta = d.get("metadata", {})
            moves.append(
                {
                    "title": meta.get("address", "Decision"),
                    "dollars": None,
                    "why": meta.get("reasoning", d.get("text", ""))[:200],
                    "recommended_action": meta.get("verdict", "Review"),
                    "deal_ref": meta.get("address"),
                    "source": meta.get("source", "brain_memory"),
                }
            )

        if moves:
            srcs = list(sources)
            if any(m.get("source") == "clickup" for m in moves):
                srcs.append("clickup")
            if any(m.get("source") != "clickup" for m in moves):
                srcs.append("brain_memory")
            return {
                "status": "ok",
                "sources": sorted(set(srcs)) or ["brain_memory"],
                "limit": limit,
                "moves": moves[:limit],
                "decisions_known": self.kb.count("decisions"),
            }

        return {
            "status": "connect_source",
            "sources": ["clickup"],
            "limit": limit,
            "moves": [],
            "decisions_known": self.kb.count("decisions"),
        }

    def blindspots(self) -> dict:
        """Surface gaps from connected sources only — never a missing-connector wall."""
        self._ensure_clickup_sync()
        items: list[dict] = []
        sources: list[str] = []

        overdue = self._clickup_overdue()
        if overdue is not None:
            sources.append("clickup")
            if len(overdue) > 5:
                items.append(
                    {
                        "title": f"{len(overdue)} overdue tasks — visibility gap",
                        "source": "clickup",
                    }
                )

        ghl_data = self._ghl_summary()
        if ghl_data is not None:
            sources.append("ghl")
            unread = int(ghl_data.get("unread_texts") or 0)
            if unread > 0:
                items.append(
                    {
                        "title": f"{unread} unread GHL conversation{'s' if unread != 1 else ''}",
                        "source": "ghl",
                    }
                )

        if fieldy.configured():
            sources.append("fieldy")
            try:
                convos = fieldy.fetch_yesterday(include_transcripts=False)
                if not convos:
                    items.append(
                        {
                            "title": "No Fieldy conversations ingested yesterday",
                            "source": "fieldy",
                        }
                    )
            except Exception:
                pass
        elif clickup.configured():
            try:
                cu = clickup.fetch_recent_transcripts(days_back=2, limit=5)
                if not cu:
                    items.append(
                        {
                            "title": "No meeting transcripts in ClickUp from the last 2 days",
                            "source": "clickup",
                        }
                    )
                sources.append("clickup")
            except Exception:
                pass

        if not sources:
            return _needs("brain_scan")

        return {
            "status": "ok",
            "sources": sources,
            "items": items,
        }

    def watchlist(self) -> dict:
        self._ensure_clickup_sync()
        items: list[dict] = []
        sources: list[str] = []

        overdue = self._clickup_overdue()
        if overdue:
            sources.append("clickup")
            for t in overdue[:5]:
                items.append(
                    {
                        "title": t["task"],
                        "detail": f"{t['person']} · {t['days_late']}d overdue",
                        "source": "clickup",
                        "clickup_task_id": t.get("clickup_task_id"),
                    }
                )

        if clickup.configured():
            try:
                open_items = clickup.open_tasks(limit=5)
                if open_items:
                    sources.append("clickup")
                    items.extend(open_items)
            except Exception:
                pass

        cal = self._calendar_today()
        if cal:
            sources.append("google_calendar")
            for ev in cal:
                items.append(
                    {
                        "title": ev["title"],
                        "detail": ev.get("start", ""),
                        "source": "google_calendar",
                    }
                )

        ghl_data = self._ghl_summary()
        if ghl_data is not None:
            sources.append("ghl")
            unread = int(ghl_data.get("unread_texts") or 0)
            missed = int(ghl_data.get("missed_calls") or 0)
            leads = int(ghl_data.get("new_leads") or 0)
            if unread > 0:
                items.append(
                    {
                        "title": f"{unread} unread text{'s' if unread != 1 else ''}",
                        "detail": "GoHighLevel inbox",
                        "source": "ghl",
                    }
                )
            if missed > 0:
                items.append(
                    {
                        "title": f"{missed} missed call{'s' if missed != 1 else ''}",
                        "detail": "GoHighLevel conversations",
                        "source": "ghl",
                    }
                )
            if leads > 0 and not unread and not missed:
                items.append(
                    {
                        "title": f"{leads} recent contact{'s' if leads != 1 else ''}",
                        "detail": "New in GHL — review pipeline",
                        "source": "ghl",
                    }
                )

        if items:
            return {"status": "ok", "sources": sources, "items": items}
        return _needs("brain_scan")

    def week_ahead(self) -> dict:
        cal = self._calendar_week()
        if cal is not None:
            return section_ok(cal, "google_calendar")
        return _needs("google_calendar")

    def team_pulse(self) -> dict:
        self._ensure_clickup_sync()
        overdue: list[dict] = []
        gaps: list[dict] = []
        sources: list[str] = []

        od = self._clickup_overdue()
        if od is not None:
            sources.append("clickup")
            overdue = od

        if fieldy.configured():
            sources.append("fieldy")
            try:
                convos = fieldy.fetch_yesterday(include_transcripts=False)
                for item in fieldy.commitments_from_convos(convos)[:5]:
                    gaps.append(
                        {
                            "person": "Lindsey",
                            "committed": item["title"],
                            "actual": "from Fieldy yesterday",
                            "suggested_move": "Confirm in ClickUp",
                        }
                    )
            except Exception:
                pass
        elif clickup.configured():
            sources.append("clickup")
            try:
                for item in clickup.fetch_fieldy_flagged_tasks(limit=5):
                    gaps.append(
                        {
                            "person": "Lindsey",
                            "committed": item.get("detail") or item.get("title", ""),
                            "actual": "flagged from Fieldy in ClickUp",
                            "suggested_move": "Close the loop",
                            "clickup_task_id": item.get("clickup_task_id"),
                        }
                    )
            except Exception:
                pass

        if overdue or gaps:
            return {
                "status": "ok",
                "sources": sources,
                "overdue": overdue,
                "gaps": gaps,
            }

        return {
            "status": "connect_source",
            "sources": ["clickup"],
            "overdue": [],
            "gaps": [],
        }

    def health_metrics(self) -> dict:
        """Display-only health data (wellbeing guardrail)."""
        metrics: dict = {}
        sources: list[str] = []

        if whoop.configured():
            try:
                metrics["whoop"] = whoop.fetch_recovery()
                sources.append("whoop")
            except Exception:
                pass

        if apple_health.configured():
            try:
                metrics["apple_health"] = apple_health.fetch_metrics()
                sources.append("apple_health")
            except Exception:
                pass

        if metrics:
            return {
                "status": "ok",
                "sources": sources,
                "metrics": metrics,
                "note": "Tracks only — never prescribes. Route clinical decisions to your provider.",
            }
        return _needs("apple_health")

    def ghl_crm(self) -> dict:
        data = self._ghl_summary()
        if data is None:
            return _needs("ghl")
        return {
            "status": "ok",
            "sources": ["ghl"],
            "new_leads": data.get("new_leads"),
            "missed_calls": data.get("missed_calls"),
            "unread_texts": data.get("unread_texts"),
            "pipeline": data.get("pipeline", []),
            "leads": data.get("leads", []),
        }

    def audio_recent(self, limit: int = 12) -> dict:
        """Fieldy + ClickUp meeting transcripts for the Echo Intel lane."""
        convos, voice_source = self._voice_convos(days_back=7)
        items: list[dict] = []
        for c in convos[:limit]:
            items.append(
                {
                    "title": c.get("title") or "Meeting transcript",
                    "detail": (c.get("transcript") or "")[:240],
                    "date": c.get("date"),
                    "source": voice_source or c.get("source", "clickup"),
                    "url": c.get("url"),
                }
            )

        if items:
            return {
                "status": "ok",
                "sources": [voice_source] if voice_source else [],
                "items": items,
            }
        if fieldy.configured() or clickup.configured():
            return {
                "status": "ok",
                "sources": [voice_source] if voice_source else [],
                "items": [],
                "note": "No transcripts in the last 7 days.",
            }
        return _needs("fieldy")

    def meta_ads(self) -> dict:
        if not meta.configured():
            return _needs("meta")
        try:
            data = meta.fetch_ads_summary()
            return {
                "status": "ok",
                "sources": ["meta"],
                **data,
            }
        except Exception:
            return _needs("meta")

    def weather(self) -> dict:
        if not weather.configured():
            return _needs("weather")
        try:
            data = weather.fetch_cleveland()
            return {
                "status": "ok",
                "sources": ["weather"],
                **data,
            }
        except Exception:
            return _needs("weather")

    def counts(self) -> dict:
        return {
            "voice": self.kb.count("voice"),
            "decisions": self.kb.count("decisions"),
            "conversation_patterns": self.kb.count("conversation_patterns"),
            "knowledge": self.kb.count("knowledge"),
        }
