"""
Shadow-mode validation (master spec §10, step 3 — "do not skip").

Before the Brain is allowed to recommend live, it has to prove it matches Lindsey's
real calls. This harness runs her historical decisions through the deterministic
rules engine and reports how often the mechanical verdict AGREES with her actual
verdict — and shows every place it doesn't, so she can see whether each divergence
was her breaking her own rule on purpose (signal) or the rules being wrong (tune them).

Two entry points:
  • validate_history(kb)      — aggregates decisions already trained via
                               /train/deal-decision (they store verdict + rules_verdict
                               + diverged at train time).
  • validate_batch(records)   — dry-run a batch of historical deals from a CSV/JSON
                               WITHOUT storing them, so you can validate 20 past calls
                               in one shot before committing to anything.

A "record" for batch mode: {address, purchase_price, arv, rehab_estimate,
monthly_rent, monthly_debt_service, other_costs, verdict, reasoning?}.

Reading the result: `match_rate` is agreement with Lindsey's calls. The spec's bar
is that the Brain matches her before it goes live — treat a low rate as "not ready",
and read `divergences` to decide whether to adjust the rules in config.py or accept
that those were deliberate exceptions.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from brain.engine.deal_math import DealInputs
from brain.training.schemas import normalize_verdict
from brain.training.service import _evaluate_or_partial


def _summarize(rows: list[dict]) -> dict:
    """rows: [{address, human_verdict, rules_verdict, diverged, ...}]"""
    n = len(rows)
    matches = sum(1 for r in rows if not r["diverged"])
    divergences = [r for r in rows if r["diverged"]]
    return {
        "n": n,
        "matches": matches,
        "mismatches": n - matches,
        "match_rate": round(matches / n, 4) if n else None,
        "divergences": divergences,
        "verdict": _readiness(n, matches),
    }


def _readiness(n: int, matches: int) -> str:
    if n == 0:
        return "NO DATA — train or load historical decisions first."
    rate = matches / n
    if n < 20:
        return f"THIN SAMPLE ({n}/20) — feed more real calls before trusting this."
    if rate >= 0.9:
        return "READY — matches your calls; safe to move toward live (still human-gated)."
    if rate >= 0.75:
        return "CLOSE — review divergences; tune rules in config.py or confirm they were intentional."
    return "NOT READY — too many mismatches; the Brain doesn't think like you yet."


def validate_history(kb) -> dict:
    """Aggregate decisions already stored in memory (trained via /train/deal-decision)."""
    rows = []
    for d in kb.decisions_history():
        m = d.get("metadata", {})
        rows.append(
            {
                "address": m.get("address"),
                "human_verdict": m.get("verdict"),
                "rules_verdict": m.get("rules_verdict"),
                "diverged": bool(m.get("diverged")),
                "reasoning": m.get("reasoning", ""),
            }
        )
    return _summarize(rows)


def validate_batch(records: list[dict]) -> dict:
    """Dry-run a batch of historical deals WITHOUT storing them."""
    rows = []
    for rec in records:
        human = normalize_verdict(str(rec.get("verdict", "")))
        inputs = DealInputs(
            purchase_price=float(rec.get("purchase_price", 0) or 0),
            rehab_estimate=float(rec.get("rehab_estimate", 0) or 0),
            arv=float(rec.get("arv", 0) or 0),
            monthly_rent=float(rec.get("monthly_rent", 0) or 0),
            monthly_debt_service=float(rec.get("monthly_debt_service", 0) or 0),
            other_costs=float(rec.get("other_costs", 0) or 0),
        )
        engine = _evaluate_or_partial(inputs)
        rules_verdict = engine["rules_verdict"]
        rows.append(
            {
                "address": rec.get("address", ""),
                "human_verdict": human,
                "rules_verdict": rules_verdict,
                "diverged": rules_verdict != human,
                "reasoning": rec.get("reasoning", ""),
                "margin_vs_arv": engine.get("margin_vs_arv"),
                "dscr": engine.get("dscr"),
            }
        )
    return _summarize(rows)


# -- loading batch files ----------------------------------------------------
def load_records(raw: str, fmt: str) -> list[dict]:
    if fmt == "json":
        data = json.loads(raw)
        return data if isinstance(data, list) else data.get("deals", [])
    if fmt == "csv":
        return list(csv.DictReader(io.StringIO(raw)))
    raise ValueError("fmt must be 'json' or 'csv'")


def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Shadow-validate historical deals against your rules.")
    ap.add_argument("path", nargs="?", help="CSV/JSON of past deals+verdicts. Omit to validate stored history.")
    args = ap.parse_args(argv)

    if args.path:
        fmt = "json" if args.path.lower().endswith("json") else "csv"
        report = validate_batch(load_records(Path(args.path).read_text(), fmt))
    else:
        from brain.memory.knowledge_base import KnowledgeBase

        report = validate_history(KnowledgeBase())

    print(f"\nShadow validation — {report['verdict']}")
    print(f"  matched {report['matches']}/{report['n']}  (rate {report['match_rate']})")
    if report["divergences"]:
        print("  divergences (your call vs rules):")
        for d in report["divergences"]:
            print(f"    {d['address'] or '(no addr)'}: you={d['human_verdict']} rules={d['rules_verdict']}  {d['reasoning'][:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(__import__("sys").argv[1:]))
