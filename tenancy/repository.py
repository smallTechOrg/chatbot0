"""SQL for tenants and the domains they own."""

from typing import Any

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
