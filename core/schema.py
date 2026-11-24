"""
Database bootstrap: make the database and its tables if they do not exist.
Connections come from the pool in db_pool.
"""

import logging
import threading
import time

import psycopg
from langchain_postgres import PostgresChatMessageHistory

from chat.prompt_store import check_and_insert_default_prompts
from core import config
from core.db_pool import RETRYABLE_ERRORS, run_with_retry

logger = logging.getLogger(__name__)

_bootstrap_lock = threading.Lock()
_bootstrap_thread = None


def ensure_database_exists(database_url=config.DATABASE_URL, database=config.db_name):
    """
    Connect to the 'postgres' system database and create *database* if missing.

    This one cannot use the pool: the pool targets the application database,
    which may not exist yet.
    """
    base_url = database_url.rsplit("/", 1)[0]
    postgres_url = f"{base_url}/postgres"

    with psycopg.connect(postgres_url, connect_timeout=config.DB_CONNECT_TIMEOUT) as temp_conn:
        temp_conn.autocommit = True
        with temp_conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{database}"')
                logger.info(f"Database '{database}' created successfully.")
            else:
                logger.info(f"Database '{database}' already exists.")


def ensure_chat_table_exists(sync_connection, table):
    """
    Use LangChain's helper to make sure the chat history table exists.
    """
    PostgresChatMessageHistory.create_tables(sync_connection, table)
    logger.info(f"Table '{table}' created or verified.")


def ensure_summaries_table_exists(sync_connection):
    """
    Create the chat_info table for storing lead information and summaries.
    """
    with sync_connection.cursor() as cur:
        # Create the chat_info table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS chat_info (
            id SERIAL PRIMARY KEY,
            session_id TEXT NOT NULL,
            contact_name TEXT,
            email TEXT,
            mobile TEXT,
            country TEXT,
            request_type TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            metadata JSONB DEFAULT '{}',

            -- Add constraint to prevent duplicate summaries for same session
            UNIQUE(session_id)
        );

        -- Create indexes for efficient querying
        CREATE INDEX IF NOT EXISTS idx_chat_info_session_id
        ON chat_info(session_id);


        CREATE INDEX IF NOT EXISTS idx_chat_info_created_at
        ON chat_info(created_at);
        """

        cur.execute(create_table_query)

        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS contact_name TEXT;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS email TEXT;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS country TEXT;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS mobile TEXT;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS request_type TEXT;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;")

        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'OPEN';")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS remarks TEXT;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS domain TEXT;")

        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;")
        # Where the chat happened: web (the widget) or whatsapp.
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS channel TEXT DEFAULT 'web';")

        # Summary columns written by periodic_summary. Older databases call
        # summary_generated_at summary_updated_at: rename it to keep the data.
        cur.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name = 'chat_info' AND column_name = 'summary_updated_at')
                   AND NOT EXISTS (SELECT 1 FROM information_schema.columns
                                   WHERE table_name = 'chat_info' AND column_name = 'summary_generated_at')
                THEN
                    ALTER TABLE chat_info RENAME COLUMN summary_updated_at TO summary_generated_at;
                END IF;
            END $$;
            """
        )
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS summary TEXT;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS summary_generated_at TIMESTAMPTZ;")
        cur.execute("ALTER TABLE chat_info ADD COLUMN IF NOT EXISTS summary_notified_at TIMESTAMPTZ;")

    logger.info("Table 'chat_info' created/verified successfully.")


def ensure_prompts_table_exists(sync_connection):
    """Make the prompts table. Columns: domain, agent_type, type, text."""
    with sync_connection.cursor() as cur:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS prompts (
            id SERIAL PRIMARY KEY,
            domain TEXT DEFAULT 'common',
            agent_type TEXT NOT NULL,
            type TEXT NOT NULL,
            "text" TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (domain, agent_type, type)
        );
        """
        cur.execute(create_table_sql)

        # Add unique constraint if it doesn't exist (for existing databases)
        alter_table_sql = """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'prompts_domain_agent_type_type_key'
            ) THEN
                ALTER TABLE prompts
                ADD CONSTRAINT prompts_domain_agent_type_type_key
                UNIQUE (domain, agent_type, type);
            END IF;
        END $$;
        """
        cur.execute(alter_table_sql)

    logger.info("Table 'prompts' created/verified successfully.")


def ensure_domains_table_exists(sync_connection):
    """Make the domains table. Columns: key, address, parent."""
    with sync_connection.cursor() as cur:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS domains (
            id SERIAL PRIMARY KEY,
            key TEXT NOT NULL,
            address TEXT UNIQUE NOT NULL,
            parent INTEGER REFERENCES domains(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        -- Insert a default row if it doesn't exist. Without DO NOTHING this
        -- raises a unique violation on every restart after the first.
        INSERT INTO domains (key, address, parent)
        VALUES ('COMMON', 'example.com', NULL)
        ON CONFLICT (address) DO NOTHING;
        """
        cur.execute(create_table_sql)
        # Who signed the domain up, from the chatbot0 sign-up form. Only the
        # main row carries them; the www row stays empty.
        cur.execute("ALTER TABLE domains ADD COLUMN IF NOT EXISTS contact_name TEXT;")
        cur.execute("ALTER TABLE domains ADD COLUMN IF NOT EXISTS email TEXT;")
        cur.execute("ALTER TABLE domains ADD COLUMN IF NOT EXISTS mobile TEXT;")

    logger.info("Table 'domains' created/verified successfully.")


def ensure_whatsapp_tables_exist(sync_connection):
    """
    whatsapp_connections: one WhatsApp business number connected to a domain.
    Its id is in the number's webhook URL (/whatsapp/webhook/<id>), so a new
    connection works at once, with no deploy. Tokens are stored encrypted
    (see core/crypto.py). Prompts follow the domain hierarchy, as on the web.

    whatsapp_messages: message ids already handled. Meta redelivers a webhook
    it thinks failed; a redelivery must not get a second answer.
    """
    with sync_connection.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS whatsapp_connections (
                id TEXT PRIMARY KEY,
                phone_number_id TEXT UNIQUE NOT NULL,
                domain_key TEXT NOT NULL,
                display_number TEXT,
                verified_name TEXT,
                access_token_enc TEXT NOT NULL,
                app_secret_enc TEXT NOT NULL,
                verify_token TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                last_message_at TIMESTAMPTZ,
                last_error TEXT,
                last_error_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS whatsapp_messages (
                message_id TEXT PRIMARY KEY,
                received_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_received_at
            ON whatsapp_messages(received_at);
            """
        )
    logger.info("Tables 'whatsapp_connections' and 'whatsapp_messages' created/verified successfully.")


SMALLTECH_TENANT = "smallTech"


def ensure_tenancy_tables_exist(sync_connection):
    """
    Tenants and their users (see auth/ and tenancy/), and the migration that puts every existing domain
    under one enabled "smallTech" tenant. Idempotent: safe on every start, and it changes nothing for
    domains that already have a tenant.

    domains.key is not unique (the www row shares its key), so a lead belongs to a tenant through
    chat_info.domain IN (SELECT key FROM domains WHERE tenant_id = ...).
    """
    with sync_connection.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS tenants (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT FALSE,
                enabled_at TIMESTAMPTZ,
                trial_conversation_limit INT NOT NULL DEFAULT 20,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                tenant_id INT NOT NULL REFERENCES tenants(id),
                email TEXT NOT NULL,
                password_hash TEXT,
                is_admin BOOLEAN NOT NULL DEFAULT FALSE,
                session_version INT NOT NULL DEFAULT 1,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_login_at TIMESTAMPTZ
            );
            CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower ON users (lower(email));
            CREATE TABLE IF NOT EXISTS user_tokens (
                token_hash TEXT PRIMARY KEY,
                user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                purpose TEXT NOT NULL CHECK (purpose IN ('invite', 'reset')),
                expires_at TIMESTAMPTZ NOT NULL,
                used_at TIMESTAMPTZ
            );
            CREATE TABLE IF NOT EXISTS login_attempts (
                id BIGSERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_login_attempts_email_time ON login_attempts (email, attempted_at);
            ALTER TABLE domains ADD COLUMN IF NOT EXISTS tenant_id INT REFERENCES tenants(id);
            -- The tenant's own Slack incoming webhook, encrypted (core/crypto.py); NULL: not set.
            ALTER TABLE tenants ADD COLUMN IF NOT EXISTS slack_webhook_enc TEXT;
            -- When each rate-limited alert (see core/throttle.py) was last sent.
            CREATE TABLE IF NOT EXISTS alert_throttle (
                key TEXT PRIMARY KEY,
                last_sent_at TIMESTAMPTZ NOT NULL
            );
            """
        )
        # The plan sets the monthly conversation cap (tenancy/plans.py). When the column is first added, the
        # smallTech tenant (our own sites) goes on the unlimited plan; every other tenant starts on "free".
        # Later changes by an admin are never overwritten, because this runs only when the column is missing.
        cur.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                               WHERE table_name = 'tenants' AND column_name = 'plan') THEN
                    ALTER TABLE tenants ADD COLUMN plan TEXT NOT NULL DEFAULT 'free';
                    UPDATE tenants SET plan = 'pro' WHERE name = 'smallTech';
                END IF;
            END $$;
            """
        )
        cur.execute(
            """
            INSERT INTO tenants (name, enabled, enabled_at, plan)
            SELECT %s, TRUE, NOW(), 'pro'
            WHERE NOT EXISTS (SELECT 1 FROM tenants WHERE name = %s)
            """,
            (SMALLTECH_TENANT, SMALLTECH_TENANT),
        )
        cur.execute(
            "UPDATE domains SET tenant_id = (SELECT id FROM tenants WHERE name = %s ORDER BY id LIMIT 1) "
            "WHERE tenant_id IS NULL",
            (SMALLTECH_TENANT,),
        )
    logger.info("Tenancy tables created/verified successfully.")


def _create_schema(sync_connection):
    """
    Create every table this app needs, on the given connection.

    Each step is committed as it completes so a failure in a later step cannot
    roll back the tables the earlier ones already created.
    """
    steps = (
        lambda conn: ensure_chat_table_exists(conn, config.table_name),
        ensure_summaries_table_exists,
        ensure_prompts_table_exists,
        ensure_domains_table_exists,
        ensure_whatsapp_tables_exist,
        ensure_tenancy_tables_exist,
        check_and_insert_default_prompts,
    )
    for step in steps:
        step(sync_connection)
        sync_connection.commit()


def _bootstrap_once():
    """One full bootstrap pass. Raises if the database is unreachable."""
    try:
        ensure_database_exists()
    except Exception as exc:
        # A managed database usually denies the 'postgres' database. This is
        # not a fault: the schema step below still works.
        logger.warning(f"Skipping the database-creation check: {exc}")

    run_with_retry(_create_schema, attempts=1, label="schema bootstrap")


def _bootstrap_loop(limit=config.DB_BOOTSTRAP_ATTEMPTS):
    """Make the schema. Retry with an increasing delay until it is done."""
    delay = config.DB_RETRY_BASE_DELAY
    for attempt in range(1, limit + 1):
        try:
            _bootstrap_once()
            logger.info(f"Database schema ready (attempt {attempt}).")
            return
        except RETRYABLE_ERRORS as exc:
            logger.error(f"Schema bootstrap attempt {attempt}/{limit} failed: {exc}")
        except Exception:
            # Continue to retry. Some faults are temporary but are not
            # connection errors.
            logger.exception(f"Schema bootstrap attempt {attempt}/{limit} failed unexpectedly")
        time.sleep(delay)
        delay = min(delay * 2, config.DB_RETRY_MAX_DELAY)

    logger.warning(f"Giving up on schema bootstrap after {limit} attempts. The app stays up.")


def init_db(wait=config.DB_STARTUP_WAIT):
    """
    Make the database and tables if they do not exist. Never raise, and never
    wait more than *wait* seconds. A background thread continues the work.
    """
    global _bootstrap_thread

    with _bootstrap_lock:
        if _bootstrap_thread is None:
            _bootstrap_thread = threading.Thread(target=_bootstrap_loop, name="db-bootstrap", daemon=True)
            _bootstrap_thread.start()

    _bootstrap_thread.join(timeout=wait)
