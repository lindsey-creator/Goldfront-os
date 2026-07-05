"""
Bulk message importer (master spec §5.5).

Accepts a file OF YOUR REAL MESSAGES — texts, emails, Slack — and feeds each one
into voice training. Paste 50 at once and it learns from all of them.

Supported formats (auto-detected by extension, override with --format):
  .txt   one message per line, OR messages separated by a blank line (auto-detected).
  .csv   columns mapped flexibly: message/text/body -> text,
         to/recipient/recipient_type -> recipient, context/category/situation -> context.
  .json  a list of objects {text|message, recipient?, context?} OR a list of strings.
  .jsonl one JSON object (or string) per line.

Metadata is optional. Any entry missing recipient/context is auto-classified
(Claude if ANTHROPIC_API_KEY is set, heuristic otherwise) — see classifier.py.

CLI:
    python -m brain.training.importers.bulk_messages messages.csv
    python -m brain.training.importers.bulk_messages dump.txt --source texts
    cat dump.txt | python -m brain.training.importers.bulk_messages -   # read stdin
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path

from brain.training.schemas import VoiceExampleIn
from brain.training.service import TrainingService

_TEXT_KEYS = ("text", "message", "body", "content", "msg")
_RECIPIENT_KEYS = ("recipient", "to", "recipient_type", "audience", "who")
_CONTEXT_KEYS = ("context", "category", "situation", "type", "tag")


def _first(d: dict, keys) -> str | None:
    for k in d:
        if k.strip().lower() in keys:
            v = d[k]
            if v is not None and str(v).strip():
                return str(v).strip()
    return None


def parse_txt(raw: str) -> list[dict]:
    raw = raw.strip("\n")
    if not raw.strip():
        return []
    # blank-line-separated blocks if any blank lines exist; else one per line
    if "\n\n" in raw:
        blocks = [b.strip() for b in raw.split("\n\n") if b.strip()]
    else:
        blocks = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    return [{"text": b} for b in blocks]


def parse_csv(raw: str) -> list[dict]:
    rows = []
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
        text = _first(row, _TEXT_KEYS)
        if not text:
            continue
        rows.append(
            {
                "text": text,
                "recipient": _first(row, _RECIPIENT_KEYS),
                "context": _first(row, _CONTEXT_KEYS),
            }
        )
    return rows


def _coerce_entry(item) -> dict | None:
    if isinstance(item, str):
        return {"text": item.strip()} if item.strip() else None
    if isinstance(item, dict):
        text = _first(item, _TEXT_KEYS)
        if not text:
            return None
        return {
            "text": text,
            "recipient": _first(item, _RECIPIENT_KEYS),
            "context": _first(item, _CONTEXT_KEYS),
        }
    return None


def parse_json(raw: str) -> list[dict]:
    data = json.loads(raw)
    if isinstance(data, dict):
        data = data.get("messages", [data])
    out = []
    for item in data:
        e = _coerce_entry(item)
        if e:
            out.append(e)
    return out


def parse_jsonl(raw: str) -> list[dict]:
    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            e = _coerce_entry(json.loads(line))
        except json.JSONDecodeError:
            e = {"text": line}  # tolerate a plain line in a .jsonl
        if e:
            out.append(e)
    return out


def parse(raw: str, fmt: str) -> list[dict]:
    return {
        "txt": parse_txt,
        "csv": parse_csv,
        "json": parse_json,
        "jsonl": parse_jsonl,
    }[fmt](raw)


def detect_format(path: str) -> str:
    ext = Path(path).suffix.lower().lstrip(".")
    return ext if ext in ("txt", "csv", "json", "jsonl") else "txt"


def import_messages(raw: str, fmt: str, source: str = "bulk", svc: TrainingService | None = None) -> dict:
    svc = svc or TrainingService()
    entries = parse(raw, fmt)
    results = []
    for e in entries:
        res = svc.train_voice(
            VoiceExampleIn(
                text=e["text"],
                recipient=e.get("recipient"),
                context=e.get("context"),
                source=source,
            )
        )
        results.append(res)
    return {
        "imported": len(results),
        "by_recipient": _tally(results, "recipient"),
        "by_context": _tally(results, "context"),
        "results": results,
    }


def _tally(results: list[dict], key: str) -> dict:
    out: dict[str, int] = {}
    for r in results:
        out[r.get(key, "?")] = out.get(r.get(key, "?"), 0) + 1
    return out


def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Bulk-import real messages into voice training.")
    ap.add_argument("path", help="file to import, or - for stdin")
    ap.add_argument("--format", choices=["txt", "csv", "json", "jsonl"], help="override auto-detect")
    ap.add_argument("--source", default="bulk", help="tag stored on each example")
    args = ap.parse_args(argv)

    if args.path == "-":
        raw = sys.stdin.read()
        fmt = args.format or "txt"
    else:
        raw = Path(args.path).read_text()
        fmt = args.format or detect_format(args.path)

    summary = import_messages(raw, fmt, source=args.source)
    print(f"Imported {summary['imported']} messages into voice.")
    print("  by recipient:", summary["by_recipient"])
    print("  by context:  ", summary["by_context"])
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
