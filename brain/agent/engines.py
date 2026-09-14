"""
Multi-model chat routing for /chat (claude | grok | muse).

HUD chips read GET /health flags. Never put secret values in health or errors.
Grok uses xAI Chat Completions. Missing XAI_API_KEY is an honest grok error —
never a silent Claude fallback. Muse without a webhook/API URL is disconnected.
"""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from brain.agent import reasoning
from brain.persona.persona import build_persona_prompt

CHAT_MODELS = ("claude", "grok", "muse")
CHAT_TIMEOUT_SECONDS = 75.0
XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_GROK_MODEL = "grok-4"

# Dedicated pool so sync Anthropic / KB work cannot occupy FastAPI's default
# threadpool (Talk Mode hammers many GET handlers that also use it).
_LLM_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="jarvis-llm")
_llm_slots: asyncio.Semaphore | None = None

_MUSE_URL_ENV = ("MUSE_WEBHOOK_URL", "MUSE_API_URL", "MUSE_WEBHOOK")
_MUSE_KEY_ENV = ("MUSE_API_KEY", "MUSE_WEBHOOK_SECRET")


def _env_set(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def anthropic_ready() -> bool:
    return _env_set("ANTHROPIC_API_KEY")


def xai_ready() -> bool:
    return _env_set("XAI_API_KEY")


def muse_ready() -> bool:
    """True only when a Muse webhook/API URL is configured (a key alone is not a link)."""
    return any(_env_set(name) for name in _MUSE_URL_ENV)


def muse_url() -> str:
    for name in _MUSE_URL_ENV:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def grok_model_name() -> str:
    return (
        (os.getenv("XAI_MODEL") or "").strip()
        or (os.getenv("GOLDFRONT_GROK_MODEL") or "").strip()
        or DEFAULT_GROK_MODEL
    )


def health_flags() -> dict[str, Any]:
    """Booleans only — never secret values. Shape the HUD chips already read."""
    claude = anthropic_ready()
    grok = xai_ready()
    muse = muse_ready()
    models = [name for name, ok in (("claude", claude), ("grok", grok), ("muse", muse)) if ok]
    return {
        "engines": {"claude": claude, "grok": grok, "muse": muse},
        "xai": grok,
        "anthropic": claude,
        "muse": muse,
        "models": models,
        "keys": {"xai": grok, "anthropic": claude, "muse": muse},
    }


def normalize_model(raw: str | None) -> str:
    """Return claude|grok|muse or raise ValueError. Case-insensitive; default claude."""
    name = (raw or "claude").strip().lower()
    aliases = {
        "": "claude",
        "claude": "claude",
        "anthropic": "claude",
        "grok": "grok",
        "xai": "grok",
        "grok-4": "grok",
        "muse": "muse",
        "rhino": "muse",
    }
    mapped = aliases.get(name)
    if mapped is None:
        raise ValueError(f"Unknown model {raw!r}. Use claude, grok, or muse.")
    return mapped


def _llm_semaphore() -> asyncio.Semaphore:
    global _llm_slots
    if _llm_slots is None:
        _llm_slots = asyncio.Semaphore(2)
    return _llm_slots


def _missing_grok(engine: dict | None) -> dict:
    return {
        "answer": None,
        "error": "XAI_API_KEY is not set on the Brain.",
        "note": "Grok is not available — XAI_API_KEY is not set. This is not Claude.",
        "engine": engine,
        "draft": None,
        "mode": "grok",
    }


def _muse_disconnected(engine: dict | None) -> dict:
    return {
        "answer": None,
        "error": "Muse link not connected",
        "note": "Muse link not connected — add MUSE_WEBHOOK_URL or MUSE_API_URL on the Brain.",
        "engine": engine,
        "draft": None,
        "mode": "muse",
    }


def _timeout_error(model: str, engine: dict | None) -> dict:
    return {
        "answer": None,
        "error": f"{model} timed out after {int(CHAT_TIMEOUT_SECONDS)}s.",
        "note": "The language model did not respond in time. /chat did not hang the Brain.",
        "engine": engine,
        "draft": None,
        "mode": "error",
    }


def _pack_text(text: str, engine: dict | None, wants_draft: bool, mode: str) -> dict:
    draft = None
    if "DRAFT:" in text:
        draft = text.split("DRAFT:", 1)[1].strip()
    return {
        "answer": text,
        "engine": engine,
        "draft": draft,
        "requires_approval": bool(draft) or wants_draft,
        "mode": mode,
    }


def _prepare_context(message: str, kb, engine: dict | None, wants_draft: bool) -> tuple[str, str, dict]:
    memory = reasoning._retrieve(kb, message)
    system = build_persona_prompt(kb=kb, query=message)
    user = reasoning.user_payload(message, engine, memory, wants_draft)
    return system, user, memory


def _claude_sync(message: str, kb, engine: dict | None, wants_draft: bool) -> dict:
    return reasoning.answer(message, kb=kb, engine=engine, wants_draft=wants_draft)


def _parse_xai_text(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("xAI returned no choices")
    message = choices[0].get("message") or {}
    text = (message.get("content") or "").strip()
    if not text:
        raise ValueError("xAI returned an empty message")
    return text


async def _grok_async(
    message: str,
    kb,
    engine: dict | None,
    wants_draft: bool,
) -> dict:
    if not xai_ready():
        return _missing_grok(engine)

    system, user, _memory = await asyncio.to_thread(
        _prepare_context, message, kb, engine, wants_draft
    )
    key = (os.getenv("XAI_API_KEY") or "").strip()
    timeout = httpx.Timeout(CHAT_TIMEOUT_SECONDS, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                XAI_CHAT_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": grok_model_name(),
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                },
            )
    except httpx.TimeoutException:
        return _timeout_error("grok", engine)
    except Exception as exc:
        return {
            "answer": None,
            "error": str(exc),
            "note": "Grok request failed. This is not Claude.",
            "engine": engine,
            "draft": None,
            "mode": "grok",
        }

    if resp.status_code >= 400:
        return {
            "answer": None,
            "error": f"xAI returned HTTP {resp.status_code}",
            "note": "Grok request failed. This is not Claude.",
            "engine": engine,
            "draft": None,
            "mode": "grok",
        }
    try:
        text = _parse_xai_text(resp.json())
    except Exception as exc:
        return {
            "answer": None,
            "error": str(exc),
            "engine": engine,
            "draft": None,
            "mode": "grok",
        }
    return _pack_text(text, engine, wants_draft, "grok")


async def _muse_async(message: str, engine: dict | None, wants_draft: bool) -> dict:
    url = muse_url()
    if not url:
        return _muse_disconnected(engine)

    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    for name in _MUSE_KEY_ENV:
        token = (os.getenv(name) or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            break

    timeout = httpx.Timeout(CHAT_TIMEOUT_SECONDS, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                headers=headers,
                json={"message": message, "model": "muse"},
            )
    except httpx.TimeoutException:
        return _timeout_error("muse", engine)
    except Exception as exc:
        return {
            "answer": None,
            "error": str(exc),
            "note": "Muse webhook/API call failed.",
            "engine": engine,
            "draft": None,
            "mode": "muse",
        }

    if resp.status_code >= 400:
        return {
            "answer": None,
            "error": f"Muse returned HTTP {resp.status_code}",
            "note": "Muse webhook/API call failed.",
            "engine": engine,
            "draft": None,
            "mode": "muse",
        }

    text = ""
    try:
        body = resp.json()
        if isinstance(body, dict):
            text = str(body.get("answer") or body.get("text") or body.get("message") or "").strip()
        elif isinstance(body, str):
            text = body.strip()
    except Exception:
        text = (resp.text or "").strip()

    if not text:
        return {
            "answer": None,
            "error": "Muse returned an empty response.",
            "engine": engine,
            "draft": None,
            "mode": "muse",
        }
    return _pack_text(text, engine, wants_draft, "muse")


async def _claude_async(message: str, kb, engine: dict | None, wants_draft: bool) -> dict:
    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(
                _LLM_POOL,
                _claude_sync,
                message,
                kb,
                engine,
                wants_draft,
            ),
            timeout=CHAT_TIMEOUT_SECONDS + 5,
        )
    except asyncio.TimeoutError:
        return _timeout_error("claude", engine)


async def answer_async(
    message: str,
    *,
    model: str = "claude",
    kb=None,
    engine: dict | None = None,
    wants_draft: bool = False,
) -> dict:
    """
    Route a chat turn. LLM work is capped and isolated from the GET threadpool.
    Missing grok/muse credentials are honest errors — never fake Claude.
    """
    try:
        lane = normalize_model(model)
    except ValueError as exc:
        return {
            "answer": None,
            "error": str(exc),
            "engine": engine,
            "draft": None,
            "mode": "error",
        }

    async with _llm_semaphore():
        if lane == "grok":
            return await _grok_async(message, kb, engine, wants_draft)
        if lane == "muse":
            return await _muse_async(message, engine, wants_draft)
        return await _claude_async(message, kb, engine, wants_draft)


def shutdown() -> None:
    _LLM_POOL.shutdown(wait=False)
