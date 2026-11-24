"""
The one place a chat model is built, so the provider, model and fallback are decided once.

The provider is the platform setting an admin saved on /admin/ (an OpenAI-compatible endpoint, core/ai_settings.py),
read through a 60-second cache. With no such setting, the Groq configuration from the environment is used.
Either way, a backup model (when set) answers any call the primary fails.
"""

from __future__ import annotations

from typing import Any

import groq
import openai
from langchain_core.runnables import Runnable
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from core import ai_settings, config

#: Used as the key for endpoints that need none (a local server): the client library insists on a value.
NO_KEY = "not-needed"


def _groq(model: str) -> ChatGroq:
    return ChatGroq(groq_api_key=config.GROQ_API_KEY, model=model)


def _openai(settings: dict[str, Any], model: str) -> ChatOpenAI:
    return ChatOpenAI(
        base_url=settings["base_url"],
        api_key=settings["api_key"] or NO_KEY,
        model=model,
        timeout=settings["timeout_seconds"],
    )


def _with_backup(primary: Runnable, backup: Runnable | None) -> Runnable:
    return primary.with_fallbacks([backup]) if backup is not None else primary  # type: ignore[attr-defined]


def models_for(settings: dict[str, Any] | None) -> list[tuple[str, str, Runnable]]:
    """[(role, model name, chat model)] for primary and, when set, backup: from *settings*, else the environment."""
    if settings:
        pairs = [("primary", settings["model"]), ("backup", settings["backup_model"])]
        return [(role, name, _openai(settings, name)) for role, name in pairs if name]
    pairs = [("primary", config.GROQ_MODEL_NAME), ("backup", config.GROQ_BACKUP_MODEL_NAME)]
    return [(role, name, _groq(name)) for role, name in pairs if name]


def get_chat_model() -> Runnable:
    """The chat model every LLM call uses (chat reply, lead capture, summaries): see the module docstring."""
    built = models_for(ai_settings.get_settings())
    primary = built[0][2]
    backup = built[1][2] if len(built) > 1 else None
    return _with_backup(primary, backup)


def is_outage(exc: BaseException) -> bool:
    """
    Whether *exc* means the model service is unavailable right now: a rate limit (429), a timeout or lost
    connection, or a 5xx, from either client library. Other errors (a bad key, a malformed request) are our bugs
    or a setup problem and stay errors.
    """
    for lib in (groq, openai):
        if isinstance(exc, (lib.RateLimitError, lib.APIConnectionError, lib.InternalServerError)):
            return True  # APIConnectionError includes APITimeoutError
        if isinstance(exc, lib.APIStatusError) and exc.status_code >= 500:
            return True
    return False
