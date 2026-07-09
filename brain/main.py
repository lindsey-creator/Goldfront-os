"""
Goldfront OS — Brain API entrypoint (master spec §4, §5).

Run:  uvicorn brain.main:app --reload

What works today: /health, /evaluate-deal (pure engine), and the full training
loop, shadow validation, cockpit read endpoints, AND the persona + reasoning
agent (/chat) — Claude when ANTHROPIC_API_KEY is set, honest fallback otherwise.
The agent narrates engine numbers, never computes them; drafts require approval.
"""

from __future__ import annotations

import threading

from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from brain.agent import reasoning
from brain.approvals import queue as approval_queue
from brain.cockpit.read import CockpitRead
from brain.connectors.base import ConnectorNotConfigured
from brain.connectors import clickup, fieldy
from brain.connectors.clickup_sync import last_sync_result, maybe_sync
from brain.connectors.status import connectors_status
from brain.engine.deal_math import DealInputs, evaluate_deal
from brain.memory.knowledge_base import KnowledgeBase
from brain.training.endpoints import router as training_router
from brain.validation import shadow

app = FastAPI(title="Goldfront OS — Brain", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "https://conradstrong.com",
        "https://www.conradstrong.com",
        "https://commandcenter.theconradteam.com",
        "https://command.theconradteam.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(training_router)


@app.on_event("startup")
def startup_clickup_sync() -> None:
    """Background pull of ClickUp into Brain memory when configured."""

    def run() -> None:
        try:
            maybe_sync(force=True)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()


class DealRequest(BaseModel):
    purchase_price: float
    rehab_estimate: float
    arv: float
    monthly_rent: float
    monthly_debt_service: float
    other_costs: float = 0.0
    flywheel_revenue_by_touch: dict[str, float] = {}


@app.get("/health")
def health():
    return {"status": "ok", "service": "goldfront-brain"}


@app.post("/evaluate-deal")
def evaluate(req: DealRequest):
    """Deterministic evaluation. This is the trustworthy core — no AI involved."""
    inputs = DealInputs(**req.model_dump())
    return evaluate_deal(inputs)


# -- Shadow-mode validation (master spec §10 step 3) ------------------------
@app.get("/validation/shadow")
def validation_shadow():
    """Aggregate stored decisions: does the Brain match your real calls yet?"""
    from brain.memory.knowledge_base import KnowledgeBase

    return shadow.validate_history(KnowledgeBase())


class ShadowBatch(BaseModel):
    deals: list[dict]


@app.post("/validation/shadow")
def validation_shadow_batch(body: ShadowBatch):
    """Dry-run a batch of past deals+verdicts without storing them."""
    return shadow.validate_batch(body.deals)


# -- Cockpit read layer (fills the Command Center modules) ------------------
_cockpit = CockpitRead()


@app.get("/brief/daily")
def brief_daily():
    return _cockpit.daily_brief()


@app.get("/money/top-moves")
def money_top_moves(limit: int = 3):
    return _cockpit.top_money_moves(limit=limit)


@app.get("/blindspots")
def blindspots():
    return _cockpit.blindspots()


@app.get("/watchlist")
def watchlist():
    return _cockpit.watchlist()


@app.get("/team/pulse")
def team_pulse():
    return _cockpit.team_pulse()


@app.get("/connectors/status")
def connectors_status_endpoint():
    """Which live connectors are configured (never exposes secrets)."""
    return connectors_status()


@app.get("/calendar/week")
def calendar_week():
    return _cockpit.week_ahead()


@app.get("/health/metrics")
def health_metrics():
    """Whoop + Apple Health display metrics (read-only)."""
    return _cockpit.health_metrics()


@app.get("/crm/ghl")
def crm_ghl():
    return _cockpit.ghl_crm()


@app.get("/audio/recent")
def audio_recent(limit: int = 12):
    """Fieldy + ClickUp transcripts for the Echo Intel lane."""
    return _cockpit.audio_recent(limit=limit)


@app.get("/ads/meta")
def ads_meta():
    return _cockpit.meta_ads()


@app.get("/weather")
def weather_cleveland():
    return _cockpit.weather()


class TaskRequest(BaseModel):
    text: str
    assignee_hint: str | None = None
    source: str | None = None


@app.post("/tasks")
def issue_task(req: TaskRequest):
    """Issue a task — queued for human approval before ClickUp (§3.3)."""
    if not clickup.configured():
        return {"status": "connect_source", "sources": ["clickup"]}
    aid = approval_queue.enqueue(
        "task",
        req.text.strip(),
        {"assignee_hint": req.assignee_hint, "source": req.source},
    )
    return {
        "status": "pending_approval",
        "approval_id": aid,
        "requires_approval": True,
        "routed_to": req.assignee_hint,
        "note": "Approve from the Command Center to create in ClickUp.",
    }


class ApprovalAction(BaseModel):
    text: str | None = None


@app.get("/approvals/pending")
def approvals_pending():
    return {"items": approval_queue.pending()}


@app.post("/approvals/{approval_id}/approve")
def approvals_approve(approval_id: str, body: ApprovalAction | None = None):
    text = body.text if body else None
    return approval_queue.approve(approval_id, content=text)


@app.post("/approvals/{approval_id}/deny")
def approvals_deny(approval_id: str):
    return approval_queue.deny(approval_id)


@app.get("/ingest/clickup/status")
def ingest_clickup_status():
    return last_sync_result()


@app.post("/ingest/clickup")
def ingest_clickup():
    """Pull full ClickUp workspace into Brain memory (force sync)."""
    result = maybe_sync(force=True)
    if result is None:
        return {"status": "connect_source", "sources": ["clickup"]}
    return result


@app.post("/ingest/fieldy")
def ingest_fieldy(days_back: int = 1):
    """Pull Fieldy conversations into Brain memory."""
    return fieldy.ingest_live(days_back=days_back)


# -- ClickUp task mutations (writes — separate from cockpit reads) ------------
class ClickUpTaskPatch(BaseModel):
    status: str | None = None
    name: str | None = None


@app.patch("/clickup/tasks/{task_id}")
def clickup_update_task(task_id: str, body: ClickUpTaskPatch):
    """Update a ClickUp task (status and/or name)."""
    if not clickup.configured():
        return {"status": "connect_source", "sources": ["clickup"]}
    if body.status is None and body.name is None:
        raise HTTPException(status_code=400, detail="Provide status and/or name")
    try:
        task = clickup.update_task(
            task_id,
            status=body.status,
            name=body.name,
        )
        return {"status": "ok", "task": task}
    except ConnectorNotConfigured:
        return {"status": "connect_source", "sources": ["clickup"]}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/clickup/tasks/{task_id}/complete")
def clickup_complete_task(task_id: str):
    """Quick-complete a ClickUp task."""
    if not clickup.configured():
        return {"status": "connect_source", "sources": ["clickup"]}
    try:
        task = clickup.complete_task(task_id)
        return {"status": "ok", "task": task}
    except ConnectorNotConfigured:
        return {"status": "connect_source", "sources": ["clickup"]}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/clickup/tasks/{task_id}/reopen")
def clickup_reopen_task(task_id: str):
    """Reopen a ClickUp task."""
    if not clickup.configured():
        return {"status": "connect_source", "sources": ["clickup"]}
    try:
        task = clickup.reopen_task(task_id)
        return {"status": "ok", "task": task}
    except ConnectorNotConfigured:
        return {"status": "connect_source", "sources": ["clickup"]}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


# -- Ask the room (reasoning agent, master spec §5.3–5.4) -------------------
class ChatRequest(BaseModel):
    message: str
    wants_draft: bool = False
    deal: DealRequest | None = None  # optional: include to get engine-grounded narration


@app.post("/chat")
def chat(req: ChatRequest):
    """
    Talk to the Brain in Lindsey's voice. If a deal is included, the deterministic
    engine runs first and the agent narrates those numbers (never computes them).
    Any draft comes back flagged requires_approval — nothing sends on its own.
    """
    engine = None
    if req.deal is not None:
        engine = evaluate_deal(DealInputs(**req.deal.model_dump()))
    result = reasoning.answer(
        req.message, kb=KnowledgeBase(), engine=engine, wants_draft=req.wants_draft
    )
    draft = result.get("draft")
    if draft:
        aid = approval_queue.enqueue("draft", draft, {"message": req.message})
        result["approval_id"] = aid
        result["requires_approval"] = True
    return result


# -- Command Center UI (production: single-port web app) --------------------
_COMMAND_CENTER_DIST = (
    Path(__file__).resolve().parent.parent.parent / "conrad-command-center" / "dist"
)


def _mount_command_center() -> None:
    """Serve built React UI from / when dist/ exists (after `npm run build`)."""
    if not _COMMAND_CENTER_DIST.is_dir():
        return
    assets = _COMMAND_CENTER_DIST / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="cc-assets")

    index_html = _COMMAND_CENTER_DIST / "index.html"

    @app.get("/", include_in_schema=False)
    def command_center_root():
        return FileResponse(index_html)

    @app.get("/{full_path:path}", include_in_schema=False)
    def command_center_spa(full_path: str):
        # API paths are registered above; this catches client-side routes only.
        if full_path.startswith("api/"):
            from fastapi import HTTPException

            raise HTTPException(status_code=404)
        candidate = _COMMAND_CENTER_DIST / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index_html)


_mount_command_center()
