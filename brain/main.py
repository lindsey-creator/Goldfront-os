"""
Goldfront OS — Brain API entrypoint (master spec §4, §5).

Run:  uvicorn brain.main:app --reload

What works today: /health, /evaluate-deal (pure engine), and the full training
loop — /train/voice, /train/deal-decision, /train/team-interaction,
/train/conversation, /decisions/history, /train/counts (master spec §5.5).
Reasoning agent + persona are still stubbed (Cowork build sequence §10).
"""

from fastapi import FastAPI
from pydantic import BaseModel

from brain.engine.deal_math import DealInputs, evaluate_deal
from brain.training.endpoints import router as training_router

app = FastAPI(title="Goldfront OS — Brain", version="0.1.0")
app.include_router(training_router)


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


# /train/* and /decisions/history are mounted above via training_router.
# TODO(cowork): mount /chat once the reasoning agent + persona are built (§5.3–5.4).
