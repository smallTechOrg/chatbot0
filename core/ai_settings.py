"""
The platform's AI provider setting (one row, admin-only): an OpenAI-compatible endpoint, its API key (encrypted with
core/crypto.py), the primary and an optional backup model, and the request timeout.

`get_settings()` is what core/llm.py reads on every model build. It caches the row in the process for at most
CACHE_SECONDS, so a change made on /admin/ reaches every instance within a minute with no redeploy. With no row
(or an unreadable database) it returns None and llm.py falls back to the Groq settings from the environment.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from psycopg.rows import dict_row

from core import crypto
from core.db_pool import with_connection

logger = logging.getLogger(__name__)

CACHE_SECONDS = 60

_lock = threading.Lock()
_cache: dict[str, Any] = {"at": None, "value": None}


@with_connection
def _read_row(conn) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT base_url, api_key_enc, model, backup_model, timeout_seconds, updated_at "
            "FROM ai_provider_settings WHERE id = 1"
        )
        return cur.fetchone()


def _decrypted(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """The row with the key decrypted, or None when there is no row or no usable key."""
    if row is None:
        return None
    key = None
    if row["api_key_enc"]:
        try:
            key = crypto.decrypt(row["api_key_enc"])
        except Exception:
            logger.error("[AI] the stored provider key cannot be decrypted; using the environment settings")
            return None
    return {
        "base_url": row["base_url"],
        "api_key": key,
        "model": row["model"],
        "backup_model": row["backup_model"],
        "timeout_seconds": row["timeout_seconds"],
    }


def get_settings() -> dict[str, Any] | None:
    """
    The provider setting with the plain API key (for llm.py only; never return this from an API), or None when the
    environment's Groq config should be used. Cached for CACHE_SECONDS. A database error keeps serving the last
    value (or None before there is one) and is retried on the next call after the cache expires.
    """
    now = time.monotonic()
    with _lock:
        if _cache["at"] is not None and now - _cache["at"] < CACHE_SECONDS:
            return _cache["value"]
    try:
        value = _decrypted(_read_row())
    except Exception:
        logger.warning("[AI] could not read the provider setting; keeping the last known one", exc_info=True)
        with _lock:
            _cache["at"] = now
            return _cache["value"]
    with _lock:
        _cache.update(at=now, value=value)
    return value


def invalidate() -> None:
    """Drop the cache so the next call reads the database (after a save on this instance)."""
    with _lock:
        _cache.update(at=None, value=None)


@with_connection
def _public_row(conn) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT base_url, model, backup_model, timeout_seconds, updated_at, api_key_enc IS NOT NULL AS key_set "
            "FROM ai_provider_settings WHERE id = 1"
        )
        return cur.fetchone()


def public_view() -> dict[str, Any] | None:
    """What the admin page may show: everything except the key (only whether one is set). None: no row."""
    return _public_row()


@with_connection
def save(conn, base_url: str, api_key: str | None, model: str, backup_model: str | None, timeout_seconds: int) -> None:
    """
    Create or replace the setting. api_key=None keeps the stored key (so the form can be saved without retyping it);
    a new key is stored encrypted.
    """
    encrypted = crypto.encrypt(api_key) if api_key else None
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ai_provider_settings (id, base_url, api_key_enc, model, backup_model, timeout_seconds)
            VALUES (1, %(url)s, %(key)s, %(model)s, %(backup)s, %(timeout)s)
            ON CONFLICT (id) DO UPDATE SET
                base_url = EXCLUDED.base_url,
                api_key_enc = COALESCE(EXCLUDED.api_key_enc, ai_provider_settings.api_key_enc),
                model = EXCLUDED.model,
                backup_model = EXCLUDED.backup_model,
                timeout_seconds = EXCLUDED.timeout_seconds,
                updated_at = NOW()
            """,
            {"url": base_url, "key": encrypted, "model": model, "backup": backup_model, "timeout": timeout_seconds},
        )
    invalidate()


@with_connection
def clear(conn) -> None:
    """Remove the setting: the environment's Groq config is used again."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM ai_provider_settings WHERE id = 1")
    invalidate()
