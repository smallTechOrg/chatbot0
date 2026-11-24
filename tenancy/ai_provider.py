"""What an admin does with the platform's AI provider setting: look at it, save it, remove it, test the connection."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from langchain_core.messages import HumanMessage

from core import ai_settings, config, llm
from core.errors import ServiceError

logger = logging.getLogger(__name__)

MAX_TEXT = 300
MIN_TIMEOUT, MAX_TIMEOUT, DEFAULT_TIMEOUT = 1, 300, 60
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class AIProviderError(ServiceError):
    """A request the API answers with `status` and a message that is safe to show."""


def status() -> dict[str, Any]:
    """The current setting without its key: {source, configured, key_set, base_url, model, backup_model, timeout}."""
    row = ai_settings.public_view()
    if row is None:
        return {
            "source": "environment",
            "base_url": None,
            "key_set": bool(config.GROQ_API_KEY),
            "model": config.GROQ_MODEL_NAME,
            "backup_model": config.GROQ_BACKUP_MODEL_NAME,
            "timeout_seconds": None,
            "updated_at": None,
        }
    return {
        "source": "database",
        "base_url": row["base_url"],
        "key_set": bool(row["key_set"]),
        "model": row["model"],
        "backup_model": row["backup_model"],
        "timeout_seconds": row["timeout_seconds"],
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def _text(raw: Any, label: str, required: bool) -> str | None:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        if required:
            raise AIProviderError(f"{label} is required.", 422)
        return None
    if not isinstance(raw, str) or len(raw.strip()) > MAX_TEXT or any(c.isspace() for c in raw.strip()):
        raise AIProviderError(f"{label} must be text without spaces, up to {MAX_TEXT} characters.", 422)
    return raw.strip()


def _base_url(raw: Any) -> str:
    url = _text(raw, "The base URL", True) or ""
    parsed = urlparse(url)
    secure = parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in _LOCAL_HOSTS)
    if not secure or not parsed.hostname:
        raise AIProviderError("The base URL must be a full https:// address (http only for localhost).", 422)
    return url.rstrip("/")


def _timeout(raw: Any) -> int:
    if raw is None:
        return DEFAULT_TIMEOUT
    if isinstance(raw, bool) or not isinstance(raw, int) or not MIN_TIMEOUT <= raw <= MAX_TIMEOUT:
        raise AIProviderError(
            f"The timeout must be a whole number of seconds from {MIN_TIMEOUT} to {MAX_TIMEOUT}.", 422
        )
    return raw


def save(data: dict[str, Any]) -> None:
    """
    Save the provider. The API key may be left out to keep the stored one; the first save needs a key only when the
    endpoint requires one, so an empty key is accepted (stored as none).
    """
    base_url = _base_url(data.get("base_url"))
    model = _text(data.get("model"), "The model", True)
    backup = _text(data.get("backup_model"), "The backup model", False)
    timeout = _timeout(data.get("timeout_seconds"))
    key = data.get("api_key")
    if key is not None and (not isinstance(key, str) or len(key) > 1000):
        raise AIProviderError("The API key must be text.", 422)
    key = key.strip() if isinstance(key, str) and key.strip() else None
    ai_settings.save(base_url, key, model or "", backup, timeout)


def clear() -> None:
    ai_settings.clear()


def _failure(exc: BaseException) -> str:
    """The error type, and the HTTP status when there is one. Never the message: it can quote request details."""
    code = getattr(exc, "status_code", None)
    name = type(exc).__name__
    return f"HTTP {code} ({name})" if code else name


def check_connection() -> list[dict[str, Any]]:
    """One tiny completion per configured model (primary, and backup if set). [{role, model, ok, error?}]"""
    ai_settings.invalidate()
    results = []
    for role, name, model in llm.models_for(ai_settings.get_settings()):
        try:
            model.bind(max_tokens=16).invoke([HumanMessage("Reply with the single word OK.")])
            results.append({"role": role, "model": name, "ok": True})
        except Exception as exc:
            logger.warning("[AI] connection test for the %s model failed: %s", role, type(exc).__name__)
            results.append({"role": role, "model": name, "ok": False, "error": _failure(exc)})
    return results
