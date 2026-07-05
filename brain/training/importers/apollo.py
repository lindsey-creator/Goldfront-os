"""
Apollo CSV importer (master spec §5.5, §7).

Apollo is your outreach tool. Export a CSV and this routes it two ways:
  • your SENT messages           -> voice training (how you write)
  • the full contact + exchange  -> conversation_patterns (how you qualify,
                                    handle objections, and close)

Apollo's export column names vary by plan and by what you include, so the
importer maps flexibly (case-insensitive, ignores spaces/underscores):

  contact name : "Contact Name" | "First Name"+"Last Name" | "Name"
  email        : "Email" | "Contact Email"
  company      : "Company" | "Company Name" | "Account"
  title        : "Title" | "Job Title"
  sent body    : "Email Body" | "Message" | "Sent Message" | "Body" | "Email Sent"
  their reply  : "Reply" | "Reply Body" | "Response" | "Replied"
  subject      : "Subject" | "Email Subject"

Rows with no sent body still create a conversation_patterns entry if a reply or
contact context exists. Empty rows are skipped.

CLI:
    python -m brain.training.importers.apollo apollo_export.csv
"""

from __future__ import annotations

import csv
import io
import sys
from pathlib import Path

from brain.training.schemas import ConversationPatternIn, VoiceExampleIn
from brain.training.service import TrainingService


def _norm(k: str) -> str:
    return "".join(ch for ch in k.lower() if ch.isalnum())


# candidate header sets, normalized
_MAP = {
    "name": ["contactname", "name", "fullname"],
    "first": ["firstname"],
    "last": ["lastname"],
    "email": ["email", "contactemail", "emailaddress"],
    "company": ["company", "companyname", "account", "accountname", "organization"],
    "title": ["title", "jobtitle", "position"],
    "sent": ["emailbody", "message", "sentmessage", "body", "emailsent", "sentbody", "bodysent"],
    "reply": ["reply", "replybody", "response", "replied", "replymessage", "theirreply"],
    "subject": ["subject", "emailsubject"],
}


def _pick(row_norm: dict, keys) -> str:
    for k in keys:
        if k in row_norm and str(row_norm[k]).strip():
            return str(row_norm[k]).strip()
    return ""


def _contact_name(row_norm: dict) -> str:
    name = _pick(row_norm, _MAP["name"])
    if name:
        return name
    first = _pick(row_norm, _MAP["first"])
    last = _pick(row_norm, _MAP["last"])
    return (first + " " + last).strip()


def import_apollo(raw: str, svc: TrainingService | None = None) -> dict:
    svc = svc or TrainingService()
    reader = csv.DictReader(io.StringIO(raw))
    voice_n = 0
    convo_n = 0
    skipped = 0

    for row in reader:
        row_norm = {_norm(k): v for k, v in row.items() if k}
        name = _contact_name(row_norm)
        email = _pick(row_norm, _MAP["email"])
        company = _pick(row_norm, _MAP["company"])
        title = _pick(row_norm, _MAP["title"])
        sent = _pick(row_norm, _MAP["sent"])
        reply = _pick(row_norm, _MAP["reply"])
        subject = _pick(row_norm, _MAP["subject"])

        if not any([sent, reply, name, email]):
            skipped += 1
            continue

        # 1) sent message -> voice
        if sent:
            svc.train_voice(
                VoiceExampleIn(
                    text=sent,
                    recipient="client",  # Apollo outreach targets prospects/clients
                    context=None,        # let the classifier tag closing/qualifying/etc.
                    source="apollo",
                )
            )
            voice_n += 1

        # 2) full exchange -> conversation_patterns
        thread_parts = []
        if subject:
            thread_parts.append(f"SUBJECT: {subject}")
        if sent:
            thread_parts.append(f"ME: {sent}")
        if reply:
            thread_parts.append(f"THEM: {reply}")
        thread = "\n".join(thread_parts)
        if thread:
            svc.train_conversation(
                ConversationPatternIn(
                    contact=name,
                    company=company,
                    title=title,
                    email=email,
                    thread=thread,
                    source="apollo",
                )
            )
            convo_n += 1

    return {
        "voice_examples": voice_n,
        "conversation_patterns": convo_n,
        "skipped": skipped,
    }


def _main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Import an Apollo CSV export into the Brain.")
    ap.add_argument("path", help="Apollo CSV export file")
    args = ap.parse_args(argv)

    raw = Path(args.path).read_text()
    summary = import_apollo(raw)
    print(
        f"Apollo import: {summary['voice_examples']} sent messages -> voice, "
        f"{summary['conversation_patterns']} exchanges -> conversation_patterns, "
        f"{summary['skipped']} rows skipped."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
