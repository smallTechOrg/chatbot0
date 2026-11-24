"""
Rate limit for alerts, shared by every Cloud Run instance through one small table: `claim` says whether the
caller may send the alert named *key* now, and records that it did. If the database is unreachable it falls back
to a per-process memory, so an outage of the database never silences or floods the alerts.
"""

import logging
import threading
import time

from core.db_pool import with_connection

logger = logging.getLogger(__name__)

_memory: dict[str, float] = {}
_memory_lock = threading.Lock()


@with_connection
def _claim_in_db(conn, key: str, interval_seconds: int) -> bool:
    """Atomic: the row is updated only when its last send is old enough, so two instances cannot both win."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO alert_throttle (key, last_sent_at) VALUES (%s, NOW())
            ON CONFLICT (key) DO UPDATE SET last_sent_at = NOW()
            WHERE alert_throttle.last_sent_at <= NOW() - make_interval(secs => %s)
            RETURNING key
            """,
            (key, interval_seconds),
        )
        return cur.fetchone() is not None


def _claim_in_memory(key: str, interval_seconds: int) -> bool:
    now = time.monotonic()
    with _memory_lock:
        last = _memory.get(key)
        if last is not None and now - last < interval_seconds:
            return False
        _memory[key] = now
        return True


def claim(key: str, interval_seconds: int = 3600) -> bool:
    """True at most once per *interval_seconds* across all instances. Never raises."""
    try:
        return _claim_in_db(key, interval_seconds)
    except Exception:
        logger.warning("[THROTTLE] database unavailable; throttling %s in memory", key, exc_info=True)
        return _claim_in_memory(key, interval_seconds)
