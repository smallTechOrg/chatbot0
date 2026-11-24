"""/api/auth/*: login, bootstrap, sessions, CSRF, rate limit, invite/reset tokens. Real database (local chatdb)."""

from datetime import timedelta

import pytest
from werkzeug.security import generate_password_hash

from auth import repository, service
from core import config, db_pool
from core.schema import SMALLTECH_TENANT
from tenancy import repository as tenants

PASSWORD = "correct horse battery"
SETUP = "setup-secret"


@pytest.fixture(autouse=True)
def clean_auth(app, monkeypatch):
    """Sessions on, shared setup password set, and no users, tokens or attempts before or after (local test DB only)."""
    monkeypatch.setattr(app, "secret_key", "test-secret")
    monkeypatch.setattr(config, "CHATBOT0_ADMIN_PASSWORD", SETUP)

    def wipe():
        with db_pool.get_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM user_tokens")
            cur.execute("DELETE FROM users")
            cur.execute("DELETE FROM login_attempts")
            cur.execute("DELETE FROM tenants WHERE name <> %s", (SMALLTECH_TENANT,))

    wipe()
    yield
    wipe()


@pytest.fixture
def tenant():
    return tenants.find_tenant_by_name(SMALLTECH_TENANT)


@pytest.fixture
def user(tenant):
    return repository.create_user(tenant["id"], "ann@example.com", generate_password_hash(PASSWORD))


def post(client, path, body=None, csrf=None):
    return client.post(path, json=body or {}, headers={"X-CSRF-Token": csrf} if csrf else {})


def sign_in(client, email="ann@example.com", password=PASSWORD):
    res = post(client, "/api/auth/login", {"email": email, "password": password})
    assert res.status_code == 200, res.get_json()
    return res.get_json()["csrf"]


# ---------------------------------------------------------------- schema and migration


def test_smalltech_tenant_exists_enabled_and_owns_every_domain(tenant):
    assert tenant["enabled"] is True
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM domains WHERE tenant_id IS NULL")
        assert cur.fetchone()[0] == 0


def test_migration_is_idempotent(tenant):
    from core.schema import ensure_tenancy_tables_exist

    with db_pool.get_connection() as conn:
        ensure_tenancy_tables_exist(conn)
        ensure_tenancy_tables_exist(conn)
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tenants WHERE name = %s", (SMALLTECH_TENANT,))
        assert cur.fetchone()[0] == 1


# ---------------------------------------------------------------- passwords and email


def test_password_is_stored_hashed(user):
    stored = repository.find_user(user["id"])["password_hash"]
    assert stored.startswith("scrypt:") and PASSWORD not in stored


@pytest.mark.parametrize("bad", ["", "short", "123456789", None, 12345678901])
def test_short_passwords_are_refused(bad):
    with pytest.raises(service.AuthError) as exc:
        service.validate_password(bad)
    assert exc.value.status == 400


@pytest.mark.parametrize("bad", ["", "nope", "a@b", "a b@c.com", None, "x" * 300 + "@a.com"])
def test_bad_emails_are_refused(bad):
    with pytest.raises(service.AuthError):
        service.normalize_email(bad)


def test_email_is_matched_case_insensitively(client, user):
    sign_in(client, email="  ANN@Example.COM ")


# ---------------------------------------------------------------- login


def test_login_returns_user_and_csrf_and_starts_a_session(client, user):
    res = post(client, "/api/auth/login", {"email": "ann@example.com", "password": PASSWORD})
    body = res.get_json()
    assert res.status_code == 200 and body["user"]["email"] == "ann@example.com"
    assert "password_hash" not in str(body) and body["csrf"]
    assert client.get("/api/auth/me").status_code == 200


def test_wrong_password_and_unknown_email_look_the_same(client, user):
    wrong = post(client, "/api/auth/login", {"email": "ann@example.com", "password": "nope-nope-nope"})
    unknown = post(client, "/api/auth/login", {"email": "who@example.com", "password": PASSWORD})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.get_json() == unknown.get_json()
    assert client.get("/api/auth/me").status_code == 401


def test_invited_user_without_a_password_cannot_log_in(client, tenant):
    repository.create_user(tenant["id"], "new@example.com", None)
    res = post(client, "/api/auth/login", {"email": "new@example.com", "password": ""})
    assert res.status_code == 401


def test_login_is_rate_limited_per_email_after_ten_failures(client, user):
    for _ in range(10):
        assert (
            post(client, "/api/auth/login", {"email": "ann@example.com", "password": "wrong-wrong-1"}).status_code
            == 401
        )
    res = post(client, "/api/auth/login", {"email": "ann@example.com", "password": PASSWORD})
    assert res.status_code == 429  # even the right password waits
    other = post(client, "/api/auth/login", {"email": "bob@example.com", "password": "wrong-wrong-1"})
    assert other.status_code == 401  # other emails are not affected


def test_a_good_login_clears_the_failures(client, user):
    for _ in range(5):
        post(client, "/api/auth/login", {"email": "ann@example.com", "password": "wrong-wrong-1"})
    sign_in(client)
    assert repository.count_recent_failures("ann@example.com", timedelta(minutes=15)) == 0


def test_old_failures_do_not_count(user):
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO login_attempts (email, attempted_at) SELECT 'ann@example.com', NOW() - INTERVAL '20 minutes' "
            "FROM generate_series(1, 12)"
        )
    assert service.login("ann@example.com", PASSWORD)["id"] == user["id"]


def test_accounts_are_off_without_a_secret_key(client, app, monkeypatch):
    monkeypatch.setattr(app, "secret_key", None)
    assert post(client, "/api/auth/login", {"email": "a@b.co", "password": "x"}).status_code == 503
    assert client.get("/api/auth/status").status_code == 503


# ---------------------------------------------------------------- me, logout, CSRF


def test_me_needs_a_session(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_user_tenant_domains_and_csrf(client, user, tenant):
    csrf = sign_in(client)
    body = client.get("/api/auth/me").get_json()
    assert body["csrf"] == csrf
    assert body["user"]["tenant_id"] == tenant["id"]
    assert body["tenant"]["name"] == SMALLTECH_TENANT and body["tenant"]["enabled"] is True
    assert body["tenant"]["trial_conversation_limit"] == 20
    assert isinstance(body["tenant"]["trial_conversations_used"], int)
    assert any(d["key"] == "COMMON" for d in body["domains"])


def test_state_changing_requests_need_the_csrf_token(client, user):
    csrf = sign_in(client)
    assert post(client, "/api/auth/logout").status_code == 403
    assert post(client, "/api/auth/logout", csrf="wrong").status_code == 403
    assert client.get("/api/auth/me").status_code == 200  # still signed in
    assert post(client, "/api/auth/logout", csrf=csrf).status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_logout_everywhere_signs_out_other_sessions(app, user):
    a, b = app.test_client(), app.test_client()
    csrf_a = sign_in(a)
    sign_in(b)
    assert b.get("/api/auth/me").status_code == 200
    assert post(a, "/api/auth/logout", {"everywhere": True}, csrf=csrf_a).status_code == 200
    assert b.get("/api/auth/me").status_code == 401


def test_a_session_dies_when_the_session_version_moves(client, user):
    sign_in(client)
    repository.bump_session_version(user["id"])
    assert client.get("/api/auth/me").status_code == 401


def test_a_tampered_cookie_is_not_a_session(client, user):
    sign_in(client)
    cookie = client.get_cookie("session")
    client.set_cookie("session", cookie.value[:-3] + "xyz")
    assert client.get("/api/auth/me").status_code == 401


# ---------------------------------------------------------------- bootstrap


def test_status_says_when_bootstrap_is_needed(client, user):
    assert client.get("/api/auth/status").get_json() == {"needs_bootstrap": True}  # a non-admin user is not an admin
    repository.create_user(user["tenant_id"], "root@example.com", generate_password_hash(PASSWORD), is_admin=True)
    assert client.get("/api/auth/status").get_json() == {"needs_bootstrap": False}


def body(**changes):
    return {"password": SETUP, "email": "root@example.com", "new_password": PASSWORD} | changes


def test_bootstrap_creates_the_first_admin_in_the_smalltech_tenant_and_signs_in(client, tenant):
    res = post(client, "/api/auth/bootstrap", body())
    assert res.status_code == 201
    assert res.get_json()["user"]["is_admin"] is True and res.get_json()["user"]["tenant_id"] == tenant["id"]
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/auth/status").get_json() == {"needs_bootstrap": False}


def test_bootstrap_works_only_once(client, app):
    assert post(client, "/api/auth/bootstrap", body()).status_code == 201
    again = post(app.test_client(), "/api/auth/bootstrap", body(email="second@example.com"))
    assert again.status_code == 409
    assert repository.find_user_by_email("second@example.com") is None


def test_the_shared_password_does_not_log_anyone_in_after_bootstrap(client):
    post(client, "/api/auth/bootstrap", body())
    res = post(client, "/api/auth/login", {"email": "root@example.com", "password": SETUP})
    assert res.status_code == 401


@pytest.mark.parametrize(
    "changes,status",
    [
        ({"password": "wrong"}, 403),
        ({"password": None}, 403),
        ({"new_password": "short"}, 400),
        ({"email": "nope"}, 400),
    ],
)
def test_bootstrap_checks_its_inputs(client, changes, status):
    assert post(client, "/api/auth/bootstrap", body(**changes)).status_code == status
    assert service.needs_bootstrap()


def test_bootstrap_is_off_without_the_shared_password(client, monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_ADMIN_PASSWORD", "")
    assert post(client, "/api/auth/bootstrap", body(password="")).status_code == 503


# ---------------------------------------------------------------- invite and reset tokens


def test_invite_token_sets_the_password_signs_in_and_works_once(app, tenant):
    invited = repository.create_user(tenant["id"], "new@example.com", None)
    token = service.issue_token(invited["id"], "invite")
    client = app.test_client()
    res = post(client, "/api/auth/accept", {"token": token, "new_password": PASSWORD})
    assert res.status_code == 200 and client.get("/api/auth/me").status_code == 200
    sign_in(app.test_client(), email="new@example.com")
    again = post(app.test_client(), "/api/auth/accept", {"token": token, "new_password": "another password 1"})
    assert again.status_code == 400


def test_tokens_are_stored_as_hashes(tenant):
    invited = repository.create_user(tenant["id"], "new@example.com", None)
    token = service.issue_token(invited["id"], "reset")
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT token_hash FROM user_tokens WHERE user_id = %s", (invited["id"],))
        stored = cur.fetchone()[0]
    assert stored != token and stored == service.hash_token(token)


def test_reset_token_changes_the_password_and_signs_out_other_sessions(app, user):
    old = app.test_client()
    sign_in(old)
    token = service.issue_token(user["id"], "reset")
    assert (
        post(
            app.test_client(), "/api/auth/accept", {"token": token, "new_password": "a brand new password"}
        ).status_code
        == 200
    )
    assert old.get("/api/auth/me").status_code == 401
    assert (
        post(app.test_client(), "/api/auth/login", {"email": "ann@example.com", "password": PASSWORD}).status_code
        == 401
    )
    sign_in(app.test_client(), password="a brand new password")


def test_expired_token_is_refused(client, user):
    repository.insert_token(service.hash_token("old-token"), user["id"], "reset", timedelta(hours=-1))
    res = post(client, "/api/auth/accept", {"token": "old-token", "new_password": PASSWORD})
    assert res.status_code == 400


def test_token_lifetimes_follow_the_plan():
    assert {"invite": timedelta(days=7), "reset": timedelta(hours=24)} == service.TOKEN_LIFETIME


@pytest.mark.parametrize("token", ["", "nonsense", None, 5])
def test_unknown_tokens_are_refused(client, token):
    assert post(client, "/api/auth/accept", {"token": token, "new_password": PASSWORD}).status_code == 400


def test_a_weak_new_password_does_not_use_up_the_token(client, user):
    token = service.issue_token(user["id"], "reset")
    assert post(client, "/api/auth/accept", {"token": token, "new_password": "short"}).status_code == 400
    assert post(client, "/api/auth/accept", {"token": token, "new_password": PASSWORD}).status_code == 200


def test_duplicate_email_cannot_be_created(tenant, user):
    assert repository.create_user(tenant["id"], "ANN@example.com", None) is None
