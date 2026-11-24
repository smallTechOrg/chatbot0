"""SQL for tenants and the domains they own."""

from datetime import datetime
from typing import Any

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row

from core.db_pool import with_connection

Tenant = dict[str, Any]


@with_connection
def find_tenant(conn, tenant_id: int) -> Tenant | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, name, enabled, enabled_at, trial_conversation_limit, plan FROM tenants WHERE id = %s",
            (tenant_id,),
        )
        return cur.fetchone()


@with_connection
def find_tenant_by_name(conn, name: str) -> Tenant | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, name, enabled, enabled_at, trial_conversation_limit, plan FROM tenants WHERE name = %s "
            "ORDER BY id LIMIT 1",
            (name,),
        )
        return cur.fetchone()


@with_connection
def set_slack_webhook(conn, tenant_id: int, encrypted: str | None) -> bool:
    """Store the tenant's encrypted Slack webhook (None clears it). False when the tenant does not exist."""
    with conn.cursor() as cur:
        cur.execute("UPDATE tenants SET slack_webhook_enc = %s WHERE id = %s", (encrypted, tenant_id))
        return cur.rowcount > 0


@with_connection
def get_slack_webhook(conn, tenant_id: int) -> str | None:
    """The tenant's encrypted Slack webhook, or None when not set."""
    with conn.cursor() as cur:
        cur.execute("SELECT slack_webhook_enc FROM tenants WHERE id = %s", (tenant_id,))
        row = cur.fetchone()
        return row[0] if row else None


@with_connection
def get_slack_prefs(conn, tenant_id: int) -> dict[str, Any] | None:
    """Slack settings that are safe to show: on/off, the dashboard link, and whether a webhook is set."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT slack_enabled AS notifications_on, slack_dashboard_url AS dashboard_url, "
            "slack_webhook_enc IS NOT NULL AS configured FROM tenants WHERE id = %s",
            (tenant_id,),
        )
        return cur.fetchone()


@with_connection
def set_slack_prefs(conn, tenant_id: int, notifications_on: bool | None, dashboard_url: str | None, clear_url: bool):
    """Change the given Slack preferences (None leaves one alone); clear_url resets the link to the default."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE tenants SET
                slack_enabled = COALESCE(%s, slack_enabled),
                slack_dashboard_url = CASE WHEN %s THEN NULL ELSE COALESCE(%s, slack_dashboard_url) END
            WHERE id = %s
            """,
            (notifications_on, clear_url, dashboard_url, tenant_id),
        )


@with_connection
def slack_routes(conn, domain_keys: list[str]) -> dict[str, tuple[int, str, str | None]]:
    """
    For each given domain key whose owning tenant has Slack on and a webhook:
    {key: (tenant_id, encrypted webhook, the tenant's dashboard link or None)}.
    A key belongs to the tenant of its first domain row, the same rule as domain_key_tenant.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT first.key, t.id, t.slack_webhook_enc, t.slack_dashboard_url
            FROM (SELECT DISTINCT ON (key) key, tenant_id FROM domains WHERE key = ANY(%s) ORDER BY key, id) first
            JOIN tenants t ON t.id = first.tenant_id
            WHERE t.slack_webhook_enc IS NOT NULL AND t.slack_enabled
            """,
            (domain_keys,),
        )
        return {key: (tenant_id, enc, url) for key, tenant_id, enc, url in cur.fetchall()}


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
def count_month_conversations(conn, tenant_id: int, since: datetime) -> int:
    """Distinct chat sessions on the tenant's domains that started at or after *since* (what the plan cap counts)."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(DISTINCT session_id) FROM chat_info "
            "WHERE created_at >= %s AND domain IN (SELECT key FROM domains WHERE tenant_id = %s)",
            (since, tenant_id),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


@with_connection
def trial_status(
    conn, domain_key: str, session_id: str, since: datetime, capped_plans: list[str]
) -> dict[str, Any] | None:
    """
    What the trial cap and the plan cap need for one chat message, in one query; None when no tenant owns the
    domain key. `used` counts all sessions (trial, tenants not enabled); `month_used` counts the sessions that
    started since *since* (enabled tenants whose plan is in *capped_plans*; 0 for the others).
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT t.enabled, t.plan,
                   t.trial_conversation_limit AS "limit",
                   EXISTS (SELECT 1 FROM chat_info WHERE session_id = %(session)s) AS has_session,
                   CASE WHEN t.enabled THEN 0 ELSE (
                       SELECT COUNT(DISTINCT c.session_id) FROM chat_info c
                       WHERE c.domain IN (SELECT key FROM domains WHERE tenant_id = t.id)
                   ) END AS used,
                   CASE WHEN t.enabled AND t.plan = ANY(%(capped)s) THEN (
                       SELECT COUNT(DISTINCT c.session_id) FROM chat_info c
                       WHERE c.created_at >= %(since)s
                         AND c.domain IN (SELECT key FROM domains WHERE tenant_id = t.id)
                   ) ELSE 0 END AS month_used
            FROM domains d JOIN tenants t ON t.id = d.tenant_id
            WHERE d.key = %(key)s
            ORDER BY d.id LIMIT 1
            """,
            {"session": session_id, "key": domain_key, "since": since, "capped": capped_plans},
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
            "SELECT d.id, d.key, d.address, d.created_at, p.key AS parent_key FROM domains d "
            "LEFT JOIN domains p ON p.id = d.parent "
            "WHERE d.tenant_id = %s AND d.address NOT LIKE 'www.%%' ORDER BY d.id",
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


# -- admin: tenants, their users and moving domains -------------------------------------------------------


@with_connection
def list_tenants_with_usage(conn, since: datetime) -> list[dict[str, Any]]:
    """Every tenant with its users, domain keys and conversation count (distinct chat sessions on its domains)."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT t.id, t.name, t.enabled, t.enabled_at, t.trial_conversation_limit, t.plan, t.created_at,
                   COALESCE((SELECT json_agg(json_build_object('id', u.id, 'email', u.email, 'is_admin', u.is_admin,
                                                                'invited', u.password_hash IS NULL,
                                                                'last_login_at', u.last_login_at) ORDER BY u.id)
                             FROM users u WHERE u.tenant_id = t.id), '[]'::json) AS users,
                   COALESCE((SELECT json_agg(DISTINCT d.key) FROM domains d WHERE d.tenant_id = t.id), '[]'::json)
                       AS domain_keys,
                   COALESCE((SELECT json_agg(json_build_object(
                                 'id', d.id, 'key', d.key, 'address', d.address, 'parent_id', d.parent,
                                 'parent_key', p.key, 'parent_address', p.address,
                                 'is_www_alias', d.address LIKE 'www.%%') ORDER BY d.id)
                             FROM domains d LEFT JOIN domains p ON p.id = d.parent
                             WHERE d.tenant_id = t.id), '[]'::json) AS domains,
                   (SELECT COUNT(DISTINCT c.session_id) FROM chat_info c
                    WHERE c.domain IN (SELECT key FROM domains WHERE tenant_id = t.id)) AS conversations,
                   (SELECT COUNT(DISTINCT c.session_id) FROM chat_info c
                    WHERE c.created_at >= %s
                      AND c.domain IN (SELECT key FROM domains WHERE tenant_id = t.id)) AS month_conversations
            FROM tenants t ORDER BY t.id
            """,
            (since,),
        )
        return cur.fetchall()


@with_connection
def update_tenant(
    conn,
    tenant_id: int,
    name: str | None,
    enabled: bool | None,
    trial_conversation_limit: int | None,
    plan: str | None = None,
) -> dict[str, Any] | None:
    """Change the given fields; enabling stamps enabled_at once. Returns the tenant, or None if unknown."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            UPDATE tenants SET
                name = COALESCE(%s, name),
                enabled = COALESCE(%s, enabled),
                enabled_at = CASE WHEN %s IS TRUE AND NOT enabled THEN NOW() ELSE enabled_at END,
                trial_conversation_limit = COALESCE(%s, trial_conversation_limit),
                plan = COALESCE(%s, plan)
            WHERE id = %s
            RETURNING id, name, enabled, enabled_at, trial_conversation_limit, plan
            """,
            (name, enabled, enabled, trial_conversation_limit, plan, tenant_id),
        )
        return cur.fetchone()


@with_connection
def move_domain(conn, key: str, tenant_id: int) -> int:
    """Give every domain row with this key (main and www) to another tenant. Returns how many rows moved."""
    with conn.cursor() as cur:
        cur.execute("UPDATE domains SET tenant_id = %s WHERE key = %s", (tenant_id, key))
        return cur.rowcount


@with_connection
def domain_keys(conn, tenant_id: int | None = None) -> list[str]:
    """Distinct domain keys, of one tenant or of all."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT key FROM domains WHERE (%(t)s::int IS NULL OR tenant_id = %(t)s::int) ORDER BY key",
            {"t": tenant_id},
        )
        return [r[0] for r in cur.fetchall()]


@with_connection
def parent_row_id(conn, key: str) -> int | None:
    """The row a child points its `parent` at for this key: the main row (not the www alias), else the first row."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM domains WHERE key = %s ORDER BY (address LIKE 'www.%%'), id LIMIT 1",
            (key,),
        )
        row = cur.fetchone()
        return row[0] if row else None


@with_connection
def set_key_parent(conn, key: str, parent_id: int) -> int:
    """Point every domain row with this key (main and www alias) at one parent row. Returns how many rows changed."""
    with conn.cursor() as cur:
        cur.execute("UPDATE domains SET parent = %s WHERE key = %s", (parent_id, key))
        return cur.rowcount
