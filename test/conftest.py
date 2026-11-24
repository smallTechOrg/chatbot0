import os
import sys

import pytest

# Add the project's root directory (the parent of 'test') to Python's search path
# This allows pytest to find and import the 'app' module.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Tests always run as a local deployment on chatdb, whatever .env says, so they
# never touch the staging or production database. Set before config is loaded:
# load_dotenv() does not override these.
os.environ["APP_ENV"] = "local"
os.environ["DB_NAME"] = "chatdb"
os.environ["DASHBOARD_URL"] = "http://localhost:3001/dashboard"

# Now that the path is set, we can import the app
from app import app as flask_app


@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    yield flask_app


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


# ---------------------------------------------------------------- tenants, users and leads (real local database)

import uuid  # noqa: E402

from werkzeug.security import generate_password_hash  # noqa: E402

TEST_PASSWORD = "correct horse battery"


class TenantWorld:
    """Builds tenants, domains, users and leads in the local test database, and removes them afterwards."""

    def __init__(self):
        self.tenants: list[int] = []
        self.sessions: list[str] = []
        self.domain_keys: list[str] = []

    def tenant(self, name: str, enabled: bool = True, limit: int = 20, plan: str = "free") -> dict:
        from core import db_pool

        with db_pool.get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tenants (name, enabled, trial_conversation_limit, plan) VALUES (%s, %s, %s, %s) "
                "RETURNING id",
                (f"{name}-{uuid.uuid4().hex[:6]}", enabled, limit, plan),
            )
            tenant_id = cur.fetchone()[0]
        self.tenants.append(tenant_id)
        key = f"T{tenant_id}_{uuid.uuid4().hex[:6]}".upper()
        self.domain(tenant_id, key, f"{key.lower()}.invalid")
        return {"id": tenant_id, "key": key}

    def domain(self, tenant_id: int, key: str, address: str | None = None) -> None:
        """A domains row. The address defaults to <key>.invalid, or gets a suffix when that exists (a www-style row)."""
        from core import db_pool

        with db_pool.get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO domains (key, address, tenant_id) VALUES (%s, %s, %s)",
                (key, address or f"{key.lower()}-{uuid.uuid4().hex[:4]}.invalid", tenant_id),
            )
        self.domain_keys.append(key)

    def user(self, tenant_id: int, email: str, is_admin: bool = False) -> dict:
        from auth import repository

        user = repository.create_user(tenant_id, email, generate_password_hash(TEST_PASSWORD), is_admin)
        assert user is not None
        return user

    def lead(self, domain_key: str, name: str = "Lead", created_at=None) -> str:
        """A chat_info row with one visitor message, so it shows in the lead list. Returns the session id."""
        from chat.history import get_session_history
        from core import db_pool

        session_id = str(uuid.uuid4())
        with db_pool.get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_info (session_id, contact_name, domain, request_type, created_at) "
                "VALUES (%s, %s, %s, 'sales', COALESCE(%s, NOW()))",
                (session_id, name, domain_key, created_at),
            )
        get_session_history(session_id).add_user_message(f"hello from {name}")
        self.sessions.append(session_id)
        return session_id

    def cleanup(self) -> None:
        from core import db_pool

        with db_pool.get_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM chat_info WHERE session_id = ANY(%s)", (self.sessions,))
            cur.execute("DELETE FROM chat_table WHERE session_id = ANY(%s::uuid[])", (self.sessions,))
            cur.execute(
                "DELETE FROM user_tokens WHERE user_id IN (SELECT id FROM users WHERE tenant_id = ANY(%s))",
                (self.tenants,),
            )
            cur.execute("DELETE FROM users WHERE tenant_id = ANY(%s)", (self.tenants,))
            cur.execute("DELETE FROM domains WHERE key = ANY(%s)", (self.domain_keys,))
            cur.execute("DELETE FROM tenants WHERE id = ANY(%s)", (self.tenants,))
            cur.execute("DELETE FROM login_attempts")


@pytest.fixture
def world(app, monkeypatch):
    """A TenantWorld, with sessions switched on (a test secret key) for sign-in."""
    monkeypatch.setattr(app, "secret_key", "test-secret")
    built = TenantWorld()
    yield built
    built.cleanup()


def sign_in(client, email: str, password: str = TEST_PASSWORD) -> str:
    """Sign a test client in; returns its CSRF token."""
    res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return res.get_json()["csrf"]
