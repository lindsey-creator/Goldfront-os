"""
Multi-model chat routing for /chat (claude | chatgpt | gemini | grok | muse).

HUD chips read GET /health flags. Never put secret values in health or errors.
Grok and ChatGPT both speak the OpenAI Chat Completions shape and share one
client; Gemini uses Google generateContent. A missing key for any lane is an
honest error for THAT lane — never a silent fallback to another model.
Muse without a webhook/API URL is disconnected.
"""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import httpx

from brain.agent import reasoning
from brain.persona.persona import build_persona_prompt

CHAT_MODELS = ("claude", "chatgpt", "gemini", "grok", "muse")
CHAT_TIMEOUT_SECONDS = 75.0

XAI_CHAT_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_GROK_MODEL = "grok-4"

OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_OPENAI_MODEL = "gpt-4o"

GEMINI_URL_TEMPLATE = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

# Dedicated pool so sync Anthropic / KB work cannot occupy FastAPI's default
# threadpool (Talk Mode hammers many GET handlers that also use it).
_LLM_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix="jarvis-llm")
_llm_slots: asyncio.Semaphore | None = None

_MUSE_URL_ENV = ("MUSE_WEBHOOK_URL", "MUSE_API_URL", "MUSE_WEBHOOK")
_MUSE_KEY_ENV = ("MUSE_API_KEY", "MUSE_WEBHOOK_SECRET")
_GEMINI_KEY_ENV = ("GEMINI_API_KEY", "GOOGLE_AI_API_KEY")


def _env_set(name: str) -> bool:
    return bool((os.getenv(name) or "").strip())


def anthropic_ready() -> bool:
    return _env_set("ANTHROPIC_API_KEY")


def xai_ready() -> bool:
    return _env_set("XAI_API_KEY")


def openai_ready() -> bool:
    return _env_set("OPENAI_API_KEY")


def gemini_ready() -> bool:
    """GEMINI_API_KEY is the Google AI Studio key — NOT the Calendar/Gmail OAuth pair."""
    return any(_env_set(name) for name in _GEMINI_KEY_ENV)


def _first_env(names: tuple[str, ...]) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


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


def openai_model_name() -> str:
    return (os.getenv("OPENAI_MODEL") or "").strip() or DEFAULT_OPENAI_MODEL


def gemini_model_name() -> str:
    return (os.getenv("GEMINI_MODEL") or "").strip() or DEFAULT_GEMINI_MODEL


def health_flags() -> dict[str, Any]:
    """Booleans only — never secret values. Shape the HUD chips already read."""
    claude = anthropic_ready()
    chatgpt = openai_ready()
    gemini = gemini_ready()
    grok = xai_ready()
    muse = muse_ready()
    ready = (
        ("claude", claude),
        ("chatgpt", chatgpt),
        ("gemini", gemini),
        ("grok", grok),
        ("muse", muse),
    )
    engines = {name: ok for name, ok in ready}
    return {
        "engines": engines,
        # Legacy top-level keys the current HUD already reads — keep them.
        "xai": grok,
        "anthropic": claude,
        "muse": muse,
        "openai": chatgpt,
        "gemini": gemini,
        "models": [name for name, ok in ready if ok],
        "keys": {
            "xai": grok,
            "anthropic": claude,
            "muse": muse,
            "openai": chatgpt,
            "gemini": gemini,
        },
    }


def normalize_model(raw: str | None) -> str:
    """Return a CHAT_MODELS lane or raise ValueError. Case-insensitive; default claude."""
    name = (raw or "claude").strip().lower()
    aliases = {
        "": "claude",
        "claude": "claude",
        "anthropic": "claude",
        "chatgpt": "chatgpt",
        "openai": "chatgpt",
        "gpt": "chatgpt",
        "gpt-4o": "chatgpt",
        "gemini": "gemini",
        "google": "gemini",
        "bard": "gemini",
        "grok": "grok",
        "xai": "grok",
        "grok-4": "grok",
        "muse": "muse",
        "rhino": "muse",
    }
    mapped = aliases.get(name)
    if mapped is None:
        raise ValueError(
            f"Unknown model {raw!r}. Use {', '.join(CHAT_MODELS)}."
        )
    return mapped


def _llm_semaphore() -> asyncio.Semaphore:
    global _llm_slots
    if _llm_slots is None:
        _llm_slots = asyncio.Semaphore(2)
    return _llm_slots


def _not_claude_suffix(lane: str) -> str:
    """
    Claude is the default lane, so a failure in any other lane must say so
    outright — a user seeing prose here should never wonder whether Claude
    quietly answered instead. Asserted by test_chat_engines.
    """
    return "" if lane == "claude" else " This is not Claude."


def _missing_key(lane: str, env_name: str, engine: dict | None) -> dict:
    """Honest per-lane failure. Never falls back to another model."""
    return {
        "answer": None,
        "error": f"{env_name} is not set on the Brain.",
        "note": (
            f"{lane} is not available — {env_name} is not set."
            f" Add it in Settings.{_not_claude_suffix(lane)}"
        ),
        "engine": engine,
        "draft": None,
        "mode": lane,
    }


def _missing_grok(engine: dict | None) -> dict:
    return _missing_key("grok", "XAI_API_KEY", engine)


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


def _parse_openai_text(payload: dict, provider: str) -> str:
    """Both xAI and OpenAI return the same Chat Completions envelope."""
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError(f"{provider} returned no choices")
    message = choices[0].get("message") or {}
    text = (message.get("content") or "").strip()
    if not text:
        raise ValueError(f"{provider} returned an empty message")
    return text


def _parse_xai_text(payload: dict) -> str:
    """Back-compat shim — existing callers and tests use this name."""
    return _parse_openai_text(payload, "xAI")


def _provider_error(lane: str, detail: str, engine: dict | None) -> dict:
    return {
        "answer": None,
        "error": detail,
        "note": f"{lane} request failed.{_not_claude_suffix(lane)}",
        "engine": engine,
        "draft": None,
        "mode": lane,
    }


async def _openai_compatible_async(
    lane: str,
    url: str,
    api_key: str,
    model_name: str,
    provider: str,
    message: str,
    kb,
    engine: dict | None,
    wants_draft: bool,
) -> dict:
    """
    One client for every provider speaking OpenAI Chat Completions.
    Grok (api.x.ai) and ChatGPT (api.openai.com) differ only in URL, key and
    model name, so they share this path rather than duplicating it.
    """
    system, user, _memory = await asyncio.to_thread(
        _prepare_context, message, kb, engine, wants_draft
    )
    timeout = httpx.Timeout(CHAT_TIMEOUT_SECONDS, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "stream": False,
                },
            )
    except httpx.TimeoutException:
        return _timeout_error(lane, engine)
    except Exception as exc:
        return _provider_error(lane, str(exc), engine)

    if resp.status_code >= 400:
        return _provider_error(lane, f"{provider} returned HTTP {resp.status_code}", engine)
    try:
        text = _parse_openai_text(resp.json(), provider)
    except Exception as exc:
        return _provider_error(lane, str(exc), engine)
    return _pack_text(text, engine, wants_draft, lane)


async def _grok_async(message: str, kb, engine: dict | None, wants_draft: bool) -> dict:
    if not xai_ready():
        return _missing_key("grok", "XAI_API_KEY", engine)
    return await _openai_compatible_async(
        "grok",
        XAI_CHAT_URL,
        (os.getenv("XAI_API_KEY") or "").strip(),
        grok_model_name(),
        "xAI",
        message, kb, engine, wants_draft,
    )


async def _chatgpt_async(message: str, kb, engine: dict | None, wants_draft: bool) -> dict:
    if not openai_ready():
        return _missing_key("chatgpt", "OPENAI_API_KEY", engine)
    return await _openai_compatible_async(
        "chatgpt",
        OPENAI_CHAT_URL,
        (os.getenv("OPENAI_API_KEY") or "").strip(),
        openai_model_name(),
        "OpenAI",
        message, kb, engine, wants_draft,
    )


def _parse_gemini_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        blocked = (payload.get("promptFeedback") or {}).get("blockReason")
        raise ValueError(
            f"Gemini returned no candidates{f' (blocked: {blocked})' if blocked else ''}"
        )
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    text = "".join(str(part.get("text") or "") for part in parts).strip()
    if not text:
        raise ValueError("Gemini returned an empty message")
    return text


async def _gemini_async(message: str, kb, engine: dict | None, wants_draft: bool) -> dict:
    """
    Google generateContent. Different envelope from OpenAI: the system prompt
    goes in system_instruction, and the reply is candidates[].content.parts[].
    """
    if not gemini_ready():
        return _missing_key("gemini", "GEMINI_API_KEY", engine)

    system, user, _memory = await asyncio.to_thread(
        _prepare_context, message, kb, engine, wants_draft
    )
    key = _first_env(_GEMINI_KEY_ENV)
    url = GEMINI_URL_TEMPLATE.format(model=gemini_model_name())
    timeout = httpx.Timeout(CHAT_TIMEOUT_SECONDS, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                url,
                # Key travels as a header, never in the URL — query strings end
                # up in proxy and access logs.
                headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                json={
                    "system_instruction": {"parts": [{"text": system}]},
                    "contents": [{"role": "user", "parts": [{"text": user}]}],
                },
            )
    except httpx.TimeoutException:
        return _timeout_error("gemini", engine)
    except Exception as exc:
        return _provider_error("gemini", str(exc), engine)

    if resp.status_code >= 400:
        return _provider_error("gemini", f"Google returned HTTP {resp.status_code}", engine)
    try:
        text = _parse_gemini_text(resp.json())
    except Exception as exc:
        return _provider_error("gemini", str(exc), engine)
    return _pack_text(text, engine, wants_draft, "gemini")


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
        if lane == "chatgpt":
            return await _chatgpt_async(message, kb, engine, wants_draft)
        if lane == "gemini":
            return await _gemini_async(message, kb, engine, wants_draft)
        if lane == "muse":
            return await _muse_async(message, engine, wants_draft)
        return await _claude_async(message, kb, engine, wants_draft)


def shutdown() -> None:
    _LLM_POOL.shutdown(wait=False)
