from http import HTTPStatus
from typing import Any

from psycopg import sql
from psycopg.rows import dict_row

from core import config
from core.db_pool import with_connection


@with_connection
def _select_chat_info(conn) -> list[dict[str, Any]]:
    # Only chats where the visitor wrote at least one message. Opening the
    # widget saves the intro message, and the periodic summary then makes a
    # chat_info row for that session; those rows are not leads.
    query = sql.SQL("""
            SELECT
                session_id,
                COALESCE(contact_name, '') as name,
                COALESCE(email, '') as email,
                COALESCE(mobile, '') as mobile_number,
                COALESCE(country, '') as country,
                COALESCE(status, 'OPEN') as status,
                COALESCE(remarks, '') as remarks,
                COALESCE(summary, '') as summary,
                COALESCE(domain) as domain,
                COALESCE(channel, 'web') as channel,
                COALESCE(created_at) as time
            FROM chat_info
            WHERE is_active is TRUE
              AND EXISTS (
                  SELECT 1 FROM {table} h
                  WHERE h.session_id::text = chat_info.session_id
                    AND h.message->>'type' = 'human'
              )
            ORDER BY created_at DESC;
        """).format(table=sql.Identifier(config.table_name))
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query)
        return cur.fetchall()


def get_all_chat_info() -> tuple[list[dict[str, Any]], HTTPStatus]:
    """
    Retrieve all stored chat info records.
    """
    try:
        return _select_chat_info(), HTTPStatus.OK

    except Exception as e:
        print("Error fetching chat-info:", e)
        raise


@with_connection
def update_contact_info(
    conn,
    session_id: str,
    name: str | None = None,
    email: str | None = None,
    mobile: str | None = None,
    country: str | None = None,
):
    """Update the contact details for a session in chat_info."""
    try:
        with conn.cursor() as cur:
            # The column is contact_name. It read "name" before, so this
            # statement always failed.
            update_query = """
                UPDATE chat_info
                SET
                    contact_name = COALESCE(%s, contact_name),
                    email        = COALESCE(%s, email),
                    mobile       = COALESCE(%s, mobile),
                    country      = COALESCE(%s, country)
                WHERE session_id = %s
                RETURNING *;
            """

            cur.execute(update_query, (name, email, mobile, country, session_id))
            updated_row = cur.fetchone()

            updates = []
            if name:
                updates.append(f"name='{name}'")
            if email:
                updates.append(f"email='{email}'")
            if mobile:
                updates.append(f"mobile='{mobile}'")
            if country:
                updates.append(f"country='{country}'")

            changed = ", ".join(updates) if updates else "no new info"
            print(f"[DATABASE] Contact updated for session {session_id}: {changed}")
            return bool(updated_row)

    except Exception as e:
        print(f"[DATABASE ERROR] Failed to update contact for {session_id}: {e!s}")
        raise


@with_connection
def update_chat_info(
    conn,
    session_id: str,
    status: str | None = None,
    remarks: str | None = None,
    is_active: bool | None = None,
):
    """
    Insert or update a row in chat_info and return the updated row.
    """
    try:
        with conn.cursor() as cur:
            update_query = """
                UPDATE chat_info
                SET
                    status = COALESCE(%s, status),
                    remarks = COALESCE(%s, remarks),
                    is_active = COALESCE(%s, is_active)
                WHERE session_id = %s
                RETURNING *;
            """

            cur.execute(update_query, (status, remarks, is_active, session_id))

            updated_row = cur.fetchone()

            # Log what was updated
            updates = []
            if status:
                updates.append(f"status='{status}'")
            if remarks:
                updates.append(f"remarks='{remarks}'")
            if is_active is not None:
                updates.append(f"is_active={1 if is_active else 0}")

            print(
                f"[DATABASE] Info updated for session {session_id}: {', '.join(updates) if updates else 'no new info'}"
            )
            return bool(updated_row)

    except Exception as e:
        print(f"[DATABASE ERROR] Failed to update lead for {session_id}: {e!s}")
        raise
