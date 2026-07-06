"""Shadow-mode validation harness."""

from brain.training.schemas import DealDecisionIn
from brain.validation import shadow


def test_validate_batch_all_match():
    records = [
        # clean GO: strong margin + strong DSCR, human agrees
        {"address": "A", "purchase_price": 80000, "arv": 200000, "rehab_estimate": 30000,
         "monthly_rent": 2000, "monthly_debt_service": 1200, "verdict": "GO"},
        # clean NO-GO: thin margin, human agrees
        {"address": "B", "purchase_price": 180000, "arv": 200000, "rehab_estimate": 30000,
         "monthly_rent": 800, "monthly_debt_service": 1000, "verdict": "NO-GO"},
    ]
    r = shadow.validate_batch(records)
    assert r["n"] == 2
    assert r["matches"] == 2
    assert r["match_rate"] == 1.0
    assert r["divergences"] == []


def test_validate_batch_flags_divergence():
    records = [
        # thin-margin deal the rules won't bless, but human said GO -> divergence
        {"address": "Override", "purchase_price": 180000, "arv": 200000, "rehab_estimate": 30000,
         "monthly_rent": 800, "monthly_debt_service": 1000, "verdict": "GO",
         "reasoning": "strategic relationship"},
    ]
    r = shadow.validate_batch(records)
    assert r["mismatches"] == 1
    assert r["divergences"][0]["human_verdict"] == "GO"
    assert r["divergences"][0]["rules_verdict"] != "GO"


def test_readiness_thin_sample():
    r = shadow.validate_batch([
        {"address": "A", "purchase_price": 80000, "arv": 200000, "rehab_estimate": 30000,
         "monthly_rent": 2000, "monthly_debt_service": 1200, "verdict": "GO"},
    ])
    assert "THIN SAMPLE" in r["verdict"]


def test_readiness_ready_when_20_and_high_match():
    records = [
        {"address": f"deal{i}", "purchase_price": 80000, "arv": 200000, "rehab_estimate": 30000,
         "monthly_rent": 2000, "monthly_debt_service": 1200, "verdict": "GO"}
        for i in range(20)
    ]
    r = shadow.validate_batch(records)
    assert r["n"] == 20
    assert r["match_rate"] == 1.0
    assert r["verdict"].startswith("READY")


def test_validate_history_from_trained_decisions(svc):
    svc.train_deal_decision(DealDecisionIn(
        address="hist1", purchase_price=80000, arv=200000, rehab_estimate=30000,
        monthly_rent=2000, monthly_debt_service=1200, verdict="GO", reasoning=""))
    svc.train_deal_decision(DealDecisionIn(
        address="hist2", purchase_price=180000, arv=200000, rehab_estimate=30000,
        monthly_rent=800, monthly_debt_service=1000, verdict="GO", reasoning="override"))
    r = shadow.validate_history(svc.kb)
    assert r["n"] == 2
    assert r["matches"] == 1          # first matches, second is an override
    assert r["mismatches"] == 1


def test_load_records_json_and_csv():
    j = shadow.load_records('[{"address":"x","verdict":"GO"}]', "json")
    assert j[0]["address"] == "x"
    c = shadow.load_records("address,verdict\ny,NO-GO\n", "csv")
    assert c[0]["verdict"] == "NO-GO"
