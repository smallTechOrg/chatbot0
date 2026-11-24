"""/api/signup, /api/domains and /api/domains/<key>/prompts."""

import uuid

import pytest
from conftest import TEST_PASSWORD, sign_in

from core import db_pool
from tenancy import sites

SUFFIX = ".signup-test.invalid"


@pytest.fixture(autouse=True)
def cleanup(app, monkeypatch):
    monkeypatch.setattr(app, "secret_key", "test-secret")
    monkeypatch.setattr(sites, "notify_signup", lambda *a, **k: notified.append(a) or True)
    notified.clear()
    yield
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM prompts WHERE domain IN (SELECT key FROM domains WHERE address LIKE %s)", (f"%{SUFFIX}",)
        )
        cur.execute("DELETE FROM domains WHERE address LIKE %s", (f"%{SUFFIX}",))
        cur.execute("DELETE FROM users WHERE email LIKE %s", ("%@signup-test.invalid",))
        cur.execute("DELETE FROM tenants WHERE name LIKE %s", (f"%{SUFFIX}",))
        cur.execute("DELETE FROM login_attempts")


notified: list = []


def body(**changes):
    n = uuid.uuid4().hex[:8]
    return {
        "name": "Jane Doe",
        "website": f"https://www.shop-{n}{SUFFIX}/about",
        "email": f"jane-{n}@signup-test.invalid",
        "password": TEST_PASSWORD,
    } | changes


def sql(query, args=()):
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, args)
        return cur.fetchall() if cur.description else None


def sign_up(client, **changes):
    payload = body(**changes)
    return payload, client.post("/api/signup", json=payload)


# ---------------------------------------------------------------- sign-up


def test_signup_creates_a_disabled_tenant_user_domain_and_signs_in(client):
    payload, res = sign_up(client, description="We fit out offices.", phone="+91 98765 43210")
    assert res.status_code == 201
    out = res.get_json()
    assert out["user"]["email"] == payload["email"] and out["user"]["is_admin"] is False and out["csrf"]
    me = client.get("/api/auth/me").get_json()
    assert me["tenant"]["enabled"] is False and me["tenant"]["trial_conversation_limit"] == 20
    key = out["domain"]["key"]
    assert [d["key"] for d in me["domains"]] == [key, key]  # the main row and its www variant
    assert sql("SELECT text FROM prompts WHERE domain = %s AND type = 'company'", (key,)) == [("We fit out offices.",)]
    assert sql(
        "SELECT contact_name, email, mobile FROM domains WHERE key = %s AND address NOT LIKE 'www.%%'", (key,)
    ) == [("Jane Doe", payload["email"], "+91 98765 43210")]
    assert sql("SELECT parent FROM domains WHERE key = %s", (key,)) == [(1,), (1,)]  # inherits prompts from COMMON


def test_signup_tells_slack_once(client):
    sign_up(client)
    assert len(notified) == 1


def test_phone_and_description_are_optional(client):
    assert sign_up(client)[1].status_code == 201


def test_the_new_user_can_log_in_again(app, client):
    payload, _ = sign_up(client)
    sign_in(app.test_client(), payload["email"])


def test_duplicate_email_is_a_409_and_creates_nothing(client, app):
    first, _ = sign_up(client)
    before = sql("SELECT COUNT(*) FROM tenants")
    _, res = sign_up(app.test_client(), email=first["email"].upper())
    assert res.status_code == 409
    assert sql("SELECT COUNT(*) FROM tenants") == before


def test_duplicate_website_is_a_409_and_creates_nothing(client, app):
    first, _ = sign_up(client)
    users_before = sql("SELECT COUNT(*) FROM users")
    _, res = sign_up(app.test_client(), website=first["website"].replace("www.", ""))
    assert res.status_code == 409
    assert sql("SELECT COUNT(*) FROM users") == users_before
    assert not notified[1:]


@pytest.mark.parametrize(
    "changes",
    [
        {"name": ""},
        {"password": "short"},
        {"email": "nope"},
        {"website": "localhost"},
        {"website": ""},
        {"phone": "abc"},
        {"description": "x" * 20001},
    ],
)
def test_signup_validates_its_input(client, changes):
    _, res = sign_up(client, **changes)
    assert res.status_code in (400, 422)
    assert sql("SELECT COUNT(*) FROM users WHERE email LIKE %s", ("%@signup-test.invalid",)) == [(0,)]


def test_signup_is_off_without_a_secret_key(client, app, monkeypatch):
    monkeypatch.setattr(app, "secret_key", None)
    assert sign_up(client)[1].status_code == 503


def test_a_failed_domain_step_leaves_no_orphan_tenant(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(sites.DomainService, "add_domain", boom)
    payload, res = sign_up(client)
    assert res.status_code == 500
    assert sql("SELECT COUNT(*) FROM users WHERE email = %s", (payload["email"],)) == [(0,)]


# ---------------------------------------------------------------- /api/domains


def test_domains_need_a_session(client):
    assert client.get("/api/domains").status_code == 401
    assert client.post("/api/domains", json={"website": "a.example.com"}).status_code == 401


def test_a_tenant_lists_only_its_own_websites(app, client, world):
    sign_up(client)
    other = world.tenant("Other")
    mine = client.get("/api/domains").get_json()["domains"]
    assert len(mine) == 1 and mine[0]["address"].endswith(SUFFIX)
    assert all(d["key"] != other["key"] for d in mine)


def test_a_disabled_tenant_cannot_add_a_website(client):
    sign_up(client)
    csrf = client.get("/api/auth/me").get_json()["csrf"]
    res = client.post(
        "/api/domains", json={"website": f"another-{uuid.uuid4().hex[:6]}{SUFFIX}"}, headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 403


def enable(client):
    me = client.get("/api/auth/me").get_json()
    sql("UPDATE tenants SET enabled = TRUE WHERE id = %s", (me["tenant"]["id"],))
    return me["csrf"]


def test_an_enabled_tenant_adds_a_website_with_its_own_key(client):
    sign_up(client)
    csrf = enable(client)
    site = f"another-{uuid.uuid4().hex[:6]}{SUFFIX}"
    res = client.post("/api/domains", json={"website": f"https://www.{site}"}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 201 and res.get_json()["domain"]["address"] == site
    assert len(client.get("/api/domains").get_json()["domains"]) == 2
    assert client.post("/api/domains", json={"website": site}, headers={"X-CSRF-Token": csrf}).status_code == 409


def test_adding_a_website_needs_csrf_and_a_valid_address(client):
    sign_up(client)
    csrf = enable(client)
    assert client.post("/api/domains", json={"website": "x.example.com"}).status_code == 403
    assert client.post("/api/domains", json={"website": "nonsense"}, headers={"X-CSRF-Token": csrf}).status_code == 422


def test_at_most_ten_websites(client):
    sign_up(client)
    csrf = enable(client)
    for i in range(9):
        res = client.post(
            "/api/domains", json={"website": f"s{i}-{uuid.uuid4().hex[:5]}{SUFFIX}"}, headers={"X-CSRF-Token": csrf}
        )
        assert res.status_code == 201
    res = client.post(
        "/api/domains", json={"website": f"s10-{uuid.uuid4().hex[:5]}{SUFFIX}"}, headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 409


# ---------------------------------------------------------------- prompts


def own_key(client):
    return client.get("/api/domains").get_json()["domains"][0]["key"]


def test_prompts_show_own_and_inherited_text(client):
    sign_up(client, description="Our own pitch.")
    key = own_key(client)
    prompts = client.get(f"/api/domains/{key}/prompts").get_json()["prompts"]
    assert prompts["company"] == {"text": "Our own pitch.", "own": True}
    assert prompts["base-prompt"]["own"] is False  # inherited from COMMON through the parent domain
    assert set(prompts) == {"company", "base-prompt", "intro-message"}


def test_a_disabled_tenant_can_read_but_not_edit_prompts(client):
    sign_up(client)
    key = own_key(client)
    csrf = client.get("/api/auth/me").get_json()["csrf"]
    assert client.get(f"/api/domains/{key}/prompts").status_code == 200
    res = client.put(f"/api/domains/{key}/prompts", json={"company": "new"}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 403


def test_an_enabled_tenant_edits_its_prompts_without_touching_the_parent(client):
    sign_up(client)
    key = own_key(client)
    csrf = enable(client)
    parent_before = sql("SELECT text FROM prompts WHERE domain = 'COMMON' ORDER BY type")
    res = client.put(
        f"/api/domains/{key}/prompts",
        json={"company": " We sell tea. ", "intro-message": "Hi!"},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 200
    got = client.get(f"/api/domains/{key}/prompts").get_json()["prompts"]
    assert got["company"] == {"text": "We sell tea.", "own": True}
    assert got["intro-message"] == {"text": "Hi!", "own": True}
    assert got["base-prompt"]["own"] is False
    assert sql("SELECT text FROM prompts WHERE domain = 'COMMON' ORDER BY type") == parent_before


def test_inheritance_through_the_parent_domain_still_reaches_the_chat_prompt(client):
    from chat.prompts import load_prompt_from_db

    sign_up(client)
    key = own_key(client)
    assert load_prompt_from_db(key, "sales", "base-prompt") == load_prompt_from_db("COMMON", "sales", "base-prompt")


@pytest.mark.parametrize("payload", [{}, {"company": ""}, {"company": 5}, {"company": "x" * 20001}, {"other": "x"}])
def test_prompt_edits_are_validated(client, payload):
    sign_up(client)
    key = own_key(client)
    csrf = enable(client)
    assert client.put(f"/api/domains/{key}/prompts", json=payload, headers={"X-CSRF-Token": csrf}).status_code == 400


def test_prompt_edits_need_csrf(client):
    sign_up(client)
    key = own_key(client)
    enable(client)
    assert client.put(f"/api/domains/{key}/prompts", json={"company": "x"}).status_code == 403


def test_a_tenant_cannot_read_or_edit_another_tenants_prompts(app, client, world):
    sign_up(client)
    csrf = enable(client)
    other = world.tenant("Other")
    assert client.get(f"/api/domains/{other['key']}/prompts").status_code == 403
    res = client.put(f"/api/domains/{other['key']}/prompts", json={"company": "hijack"}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 403
    assert sql("SELECT 1 FROM prompts WHERE domain = %s", (other["key"],)) == []


def test_unknown_website_is_a_404(client):
    sign_up(client)
    assert client.get("/api/domains/NO_SUCH_KEY/prompts").status_code == 404


def test_an_admin_can_edit_any_websites_prompts(app, client, world):
    other = world.tenant("Other")
    world.user(other["id"], "root@signup-test.invalid", is_admin=True)
    admin = app.test_client()
    csrf = sign_in(admin, "root@signup-test.invalid")
    res = admin.put(
        f"/api/domains/{other['key']}/prompts", json={"company": "set by admin"}, headers={"X-CSRF-Token": csrf}
    )
    assert res.status_code == 200
