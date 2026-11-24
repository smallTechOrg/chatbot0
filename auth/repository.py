"""SQL for users, invite/reset tokens and login attempts."""

from datetime import timedelta
from typing import Any

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from core.db_pool import with_connection

User = dict[str, Any]

_USER_COLUMNS = "id, tenant_id, email, password_hash, is_admin, session_version, created_at, last_login_at"
# Held while the first admin is created, so two bootstraps cannot both succeed.
_BOOTSTRAP_LOCK = 7_205_001


@with_connection
def find_user_by_email(conn, email: str) -> User | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_USER_COLUMNS} FROM users WHERE lower(email) = lower(%s)", (email,))
        return cur.fetchone()


@with_connection
def find_user(conn, user_id: int) -> User | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_USER_COLUMNS} FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()


@with_connection
def admin_exists(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM users WHERE is_admin)")
        return bool(cur.fetchone()[0])


@with_connection
def create_user(conn, tenant_id: int, email: str, password_hash: str | None, is_admin: bool = False) -> User | None:
    """The new user, or None when the email is taken."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"INSERT INTO users (tenant_id, email, password_hash, is_admin) VALUES (%s, %s, %s, %s) "
                f"RETURNING {_USER_COLUMNS}",
                (tenant_id, email, password_hash, is_admin),
            )
            return cur.fetchone()
    except UniqueViolation:
        return None


@with_connection
def create_first_admin(conn, tenant_id: int, email: str, password_hash: str) -> User | None:
    """Create an admin only while none exists. None: one exists already (or the email is taken)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (_BOOTSTRAP_LOCK,))
        cur.execute("SELECT EXISTS (SELECT 1 FROM users WHERE is_admin) AS found")
        if cur.fetchone()["found"]:
            return None
        try:
            cur.execute(
                f"INSERT INTO users (tenant_id, email, password_hash, is_admin) VALUES (%s, %s, %s, TRUE) "
                f"RETURNING {_USER_COLUMNS}",
                (tenant_id, email, password_hash),
            )
        except UniqueViolation:
            return None
        return cur.fetchone()


@with_connection
def set_password(conn, user_id: int, password_hash: str) -> None:
    """New password; the session version goes up, which signs the user out everywhere."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE users SET password_hash = %s, session_version = session_version + 1 WHERE id = %s",
            (password_hash, user_id),
        )


@with_connection
def bump_session_version(conn, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET session_version = session_version + 1 WHERE id = %s", (user_id,))


@with_connection
def touch_login(conn, user_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET last_login_at = NOW() WHERE id = %s", (user_id,))


# -- invite and reset tokens ------------------------------------------------------------------------------------------


@with_connection
def insert_token(conn, token_hash: str, user_id: int, purpose: str, lifetime: timedelta) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO user_tokens (token_hash, user_id, purpose, expires_at) VALUES (%s, %s, %s, NOW() + %s)",
            (token_hash, user_id, purpose, lifetime),
        )


@with_connection
def consume_token(conn, token_hash: str) -> int | None:
    """Mark a token used and return its user id; None when unknown, expired or already used. Single use."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE user_tokens SET used_at = NOW() "
            "WHERE token_hash = %s AND used_at IS NULL AND expires_at > NOW() RETURNING user_id",
            (token_hash,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else None


# -- login attempts (rate limit) --------------------------------------------------------------------------------------


@with_connection
def record_failed_attempt(conn, email: str) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM login_attempts WHERE attempted_at < NOW() - INTERVAL '1 day'")
        cur.execute("INSERT INTO login_attempts (email) VALUES (lower(%s))", (email,))


@with_connection
def count_recent_failures(conn, email: str, window: timedelta) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM login_attempts WHERE email = lower(%s) AND attempted_at > NOW() - %s",
            (email, window),
        )
        return int(cur.fetchone()[0])


@with_connection
def clear_attempts(conn, email: str) -> None:
    with conn.cursor() as cur:
        cur.execute("DELETE FROM login_attempts WHERE email = lower(%s)", (email,))
