"""All SQL for the WhatsApp integration. Credentials are stored encrypted."""

from __future__ import annotations

import secrets
import uuid

from psycopg.rows import dict_row

from core import crypto
from core.db_pool import with_connection

# Columns safe to show: never the encrypted credentials.
_PUBLIC = (
    "id, phone_number_id, domain_key, display_number, verified_name, verify_token, status, "
    "last_message_at, last_error, last_error_at, created_at, updated_at"
)


class DomainNotFound(Exception):
    pass


class NumberAlreadyConnected(Exception):
    pass


@with_connection
def list_connections(conn) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM whatsapp_connections ORDER BY created_at;")
        return cur.fetchall()


@with_connection
def get_connection(conn, connection_id: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT {_PUBLIC} FROM whatsapp_connections WHERE id = %s;", (connection_id,))
        return cur.fetchone()


@with_connection
def _credentials(conn, where: str, value: str) -> dict | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"SELECT {_PUBLIC}, access_token_enc, app_secret_enc FROM whatsapp_connections WHERE {where} = %s;",
            (value,),
        )
        return cur.fetchone()


def _with_plain_credentials(row: dict | None) -> dict | None:
    if row is None:
        return None
    row = dict(row)
    row["access_token"] = crypto.decrypt(row.pop("access_token_enc"))
    row["app_secret"] = crypto.decrypt(row.pop("app_secret_enc"))
    return row


def get_connection_with_credentials(connection_id: str) -> dict | None:
    """The connection with its decrypted access_token and app_secret. Server-side use only."""
    return _with_plain_credentials(_credentials("id", connection_id))


def get_connection_by_number(phone_number_id: str) -> dict | None:
    return _with_plain_credentials(_credentials("phone_number_id", phone_number_id))


@with_connection
def create_connection(conn, phone_number_id: str, domain_key: str, access_token: str, app_secret: str) -> dict:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT 1 FROM domains WHERE key = %s LIMIT 1;", (domain_key,))
        if not cur.fetchone():
            raise DomainNotFound(domain_key)
        cur.execute("SELECT 1 FROM whatsapp_connections WHERE phone_number_id = %s;", (phone_number_id,))
        if cur.fetchone():
            raise NumberAlreadyConnected(phone_number_id)
        cur.execute(
            f"""
            INSERT INTO whatsapp_connections
                (id, phone_number_id, domain_key, access_token_enc, app_secret_enc, verify_token)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING {_PUBLIC};
            """,
            (
                str(uuid.uuid4()),
                phone_number_id,
                domain_key,
                crypto.encrypt(access_token),
                crypto.encrypt(app_secret),
                secrets.token_urlsafe(24),
            ),
        )
        return cur.fetchone()


@with_connection
def update_credentials(
    conn,
    connection_id: str,
    access_token: str | None = None,
    app_secret: str | None = None,
    domain_key: str | None = None,
) -> bool:
    """Replace any of the token, app secret or domain. Clears the error state."""
    with conn.cursor() as cur:
        if domain_key:
            cur.execute("SELECT 1 FROM domains WHERE key = %s LIMIT 1;", (domain_key,))
            if not cur.fetchone():
                raise DomainNotFound(domain_key)
        cur.execute(
            """
            UPDATE whatsapp_connections SET
                access_token_enc = COALESCE(%s, access_token_enc),
                app_secret_enc   = COALESCE(%s, app_secret_enc),
                domain_key       = COALESCE(%s, domain_key),
                status = CASE WHEN status = 'needs_attention' THEN 'pending' ELSE status END,
                last_error = NULL, last_error_at = NULL,
                updated_at = NOW()
            WHERE id = %s;
            """,
            (
                crypto.encrypt(access_token) if access_token else None,
                crypto.encrypt(app_secret) if app_secret else None,
                domain_key or None,
                connection_id,
            ),
        )
        return cur.rowcount > 0


@with_connection
def mark_checked(conn, connection_id: str, display_number: str | None, verified_name: str | None) -> None:
    """The token worked against the Graph API."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE whatsapp_connections SET
                display_number = COALESCE(%s, display_number),
                verified_name  = COALESCE(%s, verified_name),
                status = 'active', last_error = NULL, last_error_at = NULL, updated_at = NOW()
            WHERE id = %s;
            """,
            (display_number, verified_name, connection_id),
        )


@with_connection
def mark_inbound(conn, connection_id: str) -> None:
    """A signed message arrived: the webhook is wired up."""
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE whatsapp_connections SET last_message_at = NOW(),
                status = CASE WHEN status = 'pending' THEN 'active' ELSE status END
            WHERE id = %s;
            """,
            (connection_id,),
        )


@with_connection
def mark_error(conn, connection_id: str, error: str, needs_attention: bool) -> bool:
    """
    Record the last error. With *needs_attention*, flag the connection; returns
    True only when it was not flagged before, so an alert goes out once.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM whatsapp_connections WHERE id = %s FOR UPDATE;", (connection_id,))
        row = cur.fetchone()
        if row is None:
            return False
        cur.execute(
            """
            UPDATE whatsapp_connections SET last_error = %s, last_error_at = NOW(),
                status = CASE WHEN %s THEN 'needs_attention' ELSE status END
            WHERE id = %s;
            """,
            (error[:500], needs_attention, connection_id),
        )
        return bool(needs_attention and row[0] != "needs_attention")


@with_connection
def claim_message(conn, message_id: str) -> bool:
    """
    Record a webhook message id. True the first time, False when Meta
    redelivers it. Ids older than 7 days are dropped (Meta retries for at most 7).
    """
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO whatsapp_messages (message_id) VALUES (%s) ON CONFLICT DO NOTHING;",
            (message_id,),
        )
        first = cur.rowcount > 0
        if first and secrets.randbelow(100) == 0:
            cur.execute("DELETE FROM whatsapp_messages WHERE received_at < NOW() - INTERVAL '7 days';")
        return first


@with_connection
def ensure_chat_info(conn, session_id: str, domain: str, request_type: str, mobile: str, name: str | None) -> None:
    """
    Make the lead row for a WhatsApp chat: channel 'whatsapp', the sender's
    number as mobile, their WhatsApp profile name as contact name. Both only
    fill blanks: what the person later says in the chat wins.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO chat_info (session_id, request_type, domain, channel, mobile, contact_name)
            VALUES (%s, %s, %s, 'whatsapp', %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
                channel = 'whatsapp',
                domain = EXCLUDED.domain,
                mobile = COALESCE(chat_info.mobile, EXCLUDED.mobile),
                contact_name = COALESCE(chat_info.contact_name, EXCLUDED.contact_name);
            """,
            (session_id, request_type, domain, mobile, name),
        )
