"""
Goldfront OS — Brain API entrypoint (master spec §4, §5).

Run:  uvicorn brain.main:app --reload

What works today: /health and /evaluate-deal (pure engine, no AI, no keys).
Everything else is stubbed and gets built in Cowork per the sequence in §10.
"""

from fastapi import FastAPI
from pydantic import BaseModel

from brain.engine.deal_math import DealInputs, evaluate_deal

app = FastAPI(title="Goldfront OS — Brain", version="0.1.0")


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


# TODO(cowork): mount /train/*, /decisions/history, /chat once the Brain
# components (memory, persona, agent, training) are built. See master-spec §10.
