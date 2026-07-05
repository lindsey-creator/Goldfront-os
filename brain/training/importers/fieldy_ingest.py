"""
Fieldy ingestion adapter (real-world conversation feed).

You wear Fieldy daily; it records and transcribes your real conversations. This
turns that stream into memory: how you actually talk, qualify, coach, and close —
the highest-signal voice data there is, because it's you unscripted.

Same split as the ClickUp adapter (OAuth can't run headless):

    • ingest_conversations(convos, svc)  — pure, testable routing.
    • fetch_and_ingest(fetcher, svc)      — calls a fetcher you pass in. In Cowork,
                                            wrap the Fieldy MCP tools
                                            (fieldy_list_recent_conversations,
                                            fieldy_list_conversations_in_time_range,
                                            fieldy_get_conversation). In tests, a fake.

Routing per conversation:
    • full transcript  -> conversation_patterns (the exchange, for pattern learning)
    • your utterances   -> voice (auto-classified; how you speak)

Conversation shape a fetcher must return: list of dicts, each:
    {
      "id": "conv123",
      "title": "Call with Bobby re: 8-door refi",   # optional
      "date": "2026-07-04",                          # optional
      "transcript": "full text …",                    # used for conversation_patterns
      "my_utterances": ["…", "…"],                    # optional; your lines only
      "speaker_me": "Lindsey"                          # optional; used to extract your
                                                       # lines from a labeled transcript
    }

If `my_utterances` is absent but the transcript is speaker-labeled and
`speaker_me` is given, we extract lines that start with that speaker.
"""

from __future__ import annotations

import re
from typing import Callable

from brain.training.schemas import ConversationPatternIn, VoiceExampleIn
from brain.training.service import TrainingService


def _extract_my_lines(transcript: str, speaker_me: str | None) -> list[str]:
    if not speaker_me or not transcript:
        return []
    lines = []
    pat = re.compile(rf"^\s*{re.escape(speaker_me)}\s*[:\-]\s*(.+)$", re.IGNORECASE)
    for ln in transcript.splitlines():
        m = pat.match(ln)
        if m and m.group(1).strip():
            lines.append(m.group(1).strip())
    return lines


def ingest_conversations(convos: list[dict], svc: TrainingService | None = None) -> dict:
    svc = svc or TrainingService()
    convo_n = 0
    voice_n = 0
    skipped = 0

    for c in convos:
        transcript = (c.get("transcript") or "").strip()
        title = c.get("title") or ""
        date = c.get("date") or ""

        my_lines = c.get("my_utterances") or _extract_my_lines(transcript, c.get("speaker_me"))

        if not transcript and not my_lines:
            skipped += 1
            continue

        # full transcript -> conversation_patterns
        if transcript:
            header = " | ".join(p for p in [title, date] if p)
            thread = f"[FIELDY {header}]\n{transcript}" if header else transcript
            svc.train_conversation(
                ConversationPatternIn(
                    contact=title,
                    thread=thread,
                    source="fieldy",
                )
            )
            convo_n += 1

        # your utterances -> voice
        for line in my_lines:
            svc.train_voice(
                VoiceExampleIn(text=line, recipient=None, context=None, source="fieldy")
            )
            voice_n += 1

    return {
        "conversations": convo_n,
        "voice_examples": voice_n,
        "skipped": skipped,
    }


def fetch_and_ingest(fetcher: Callable[[], list[dict]], svc: TrainingService | None = None) -> dict:
    """
    `fetcher` returns conversations (see module docstring). In Cowork this wraps
    the Fieldy MCP tools; a daily scheduled task can call it to keep the Brain
    current — "watch Fieldy" = run this each morning over yesterday's window.
    """
    return ingest_conversations(fetcher(), svc)
