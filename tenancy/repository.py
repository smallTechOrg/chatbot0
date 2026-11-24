"""SQL for tenants and the domains they own."""

from typing import Any

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from core.db_pool import with_connection

Tenant = dict[str, Any]


@with_connection
def find_tenant(conn, tenant_id: int) -> Tenant | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, name, enabled, enabled_at, trial_conversation_limit FROM tenants WHERE id = %s",
            (tenant_id,),
        )
        return cur.fetchone()


@with_connection
def find_tenant_by_name(conn, name: str) -> Tenant | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, name, enabled, enabled_at, trial_conversation_limit FROM tenants WHERE name = %s "
            "ORDER BY id LIMIT 1",
            (name,),
        )
        return cur.fetchone()


@with_connection
def list_domains(conn, tenant_id: int) -> list[dict[str, Any]]:
    """The tenant's domain rows (main and www rows), by id."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, key, address FROM domains WHERE tenant_id = %s ORDER BY id", (tenant_id,))
        return cur.fetchall()


@with_connection
def count_conversations(conn, tenant_id: int) -> int:
    """Distinct chat sessions on the tenant's domains (what the trial cap counts)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(DISTINCT session_id) FROM chat_info "
            "WHERE domain IN (SELECT key FROM domains WHERE tenant_id = %s)",
            (tenant_id,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


@with_connection
def trial_status(conn, domain_key: str, session_id: str) -> dict[str, Any] | None:
    """What the trial cap needs for one chat message, in one query; None when no tenant owns the domain key."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT t.enabled,
                   t.trial_conversation_limit AS "limit",
                   EXISTS (SELECT 1 FROM chat_info WHERE session_id = %s) AS has_session,
                   CASE WHEN t.enabled THEN 0 ELSE (
                       SELECT COUNT(DISTINCT c.session_id) FROM chat_info c
                       WHERE c.domain IN (SELECT key FROM domains WHERE tenant_id = t.id)
                   ) END AS used
            FROM domains d JOIN tenants t ON t.id = d.tenant_id
            WHERE d.key = %s
            ORDER BY d.id LIMIT 1
            """,
            (session_id, domain_key),
        )
        return cur.fetchone()


@with_connection
def create_tenant_with_user(conn, name: str, email: str, password_hash: str) -> dict[str, Any] | None:
    """A new disabled tenant and its first user, in one transaction. None when the email is taken."""
    try:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("INSERT INTO tenants (name) VALUES (%s) RETURNING id", (name,))
            tenant_id = cur.fetchone()["id"]
            cur.execute(
                "INSERT INTO users (tenant_id, email, password_hash) VALUES (%s, %s, %s) "
                "RETURNING id, tenant_id, email, is_admin, session_version",
                (tenant_id, email, password_hash),
            )
            return cur.fetchone()
    except UniqueViolation:
        return None


@with_connection
def delete_new_tenant(conn, tenant_id: int) -> None:
    """Undo a sign-up that failed half way: the tenant, its users and any domain rows it already got."""
    with conn.cursor() as cur:
        cur.execute("DELETE FROM domains WHERE tenant_id = %s", (tenant_id,))
        cur.execute("DELETE FROM users WHERE tenant_id = %s", (tenant_id,))
        cur.execute("DELETE FROM tenants WHERE id = %s", (tenant_id,))


@with_connection
def list_sites(conn, tenant_id: int) -> list[dict[str, Any]]:
    """The tenant's websites: its main domain rows (the www variants are not listed)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, key, address, created_at FROM domains "
            "WHERE tenant_id = %s AND address NOT LIKE 'www.%%' ORDER BY id",
            (tenant_id,),
        )
        return cur.fetchall()


@with_connection
def domain_key_tenant(conn, key: str) -> int | None:
    """The tenant that owns a domain key (None: unknown key, or a key no tenant owns)."""
    with conn.cursor() as cur:
        cur.execute("SELECT tenant_id FROM domains WHERE key = %s ORDER BY id LIMIT 1", (key,))
        row = cur.fetchone()
        return row[0] if row else None


@with_connection
def domain_key_exists(conn, key: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM domains WHERE key = %s LIMIT 1", (key,))
        return cur.fetchone() is not None
