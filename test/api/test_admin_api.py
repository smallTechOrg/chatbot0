"""/api/admin/*: tenants, invite and reset links, moving domains. Admins only."""

import pytest
from conftest import sign_in

from core import db_pool


@pytest.fixture
def setup(world):
    a, b = world.tenant("A", enabled=False, limit=3), world.tenant("B")
    world.user(a["id"], "user-a@admin-test.invalid")
    world.user(a["id"], "root@admin-test.invalid", is_admin=True)
    world.lead(a["key"])
    return {"a": a, "b": b}


def as_user(app, email):
    client = app.test_client()
    return client, {"X-CSRF-Token": sign_in(client, email)}


def sql(query, args=()):
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, args)
        return cur.fetchall() if cur.description else None


def test_everything_is_admin_only(app, setup):
    client, csrf = as_user(app, "user-a@admin-test.invalid")
    tid = setup["a"]["id"]
    assert client.get("/api/admin/tenants").status_code == 403
    assert client.patch(f"/api/admin/tenants/{tid}", json={"enabled": True}, headers=csrf).status_code == 403
    assert client.post(f"/api/admin/tenants/{tid}/users", json={"email": "x@y.co"}, headers=csrf).status_code == 403
    assert client.post("/api/admin/users/1/reset-link", headers=csrf).status_code == 403
    assert (
        client.patch(f"/api/admin/domains/{setup['a']['key']}", json={"tenant_id": tid}, headers=csrf).status_code
        == 403
    )
    assert sql("SELECT enabled FROM tenants WHERE id = %s", (tid,)) == [(False,)]


def test_anonymous_requests_are_401(client):
    assert client.get("/api/admin/tenants").status_code == 401


def test_tenants_are_listed_with_usage_users_and_domains(app, setup):
    admin, _ = as_user(app, "root@admin-test.invalid")
    tenants = {t["id"]: t for t in admin.get("/api/admin/tenants").get_json()["tenants"]}
    a = tenants[setup["a"]["id"]]
    assert a["enabled"] is False and a["trial_conversation_limit"] == 3 and a["conversations"] == 1
    assert {u["email"] for u in a["users"]} == {"user-a@admin-test.invalid", "root@admin-test.invalid"}
    assert a["domain_keys"] == [setup["a"]["key"]]
    assert "password_hash" not in str(a)


def test_admin_enables_a_tenant_and_changes_its_limit_and_name(app, setup):
    admin, csrf = as_user(app, "root@admin-test.invalid")
    tid = setup["a"]["id"]
    res = admin.patch(
        f"/api/admin/tenants/{tid}",
        json={"enabled": True, "trial_conversation_limit": 50, "name": " Acme "},
        headers=csrf,
    )
    t = res.get_json()["tenant"]
    assert (t["enabled"], t["trial_conversation_limit"], t["name"]) == (True, 50, "Acme")
    assert t["enabled_at"] is not None


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"enabled": "yes"},
        {"trial_conversation_limit": -1},
        {"trial_conversation_limit": "5"},
        {"trial_conversation_limit": True},
        {"name": ""},
    ],
)
def test_tenant_updates_are_validated(app, setup, body):
    admin, csrf = as_user(app, "root@admin-test.invalid")
    assert admin.patch(f"/api/admin/tenants/{setup['a']['id']}", json=body, headers=csrf).status_code == 400


def test_unknown_tenant_is_404_and_csrf_is_required(app, setup):
    admin, csrf = as_user(app, "root@admin-test.invalid")
    assert admin.patch("/api/admin/tenants/999999", json={"enabled": True}, headers=csrf).status_code == 404
    assert admin.patch(f"/api/admin/tenants/{setup['a']['id']}", json={"enabled": True}).status_code == 403


def test_enabling_lifts_the_trial_cap_for_chat(app, client, setup):
    from tenancy import service

    key = setup["a"]["key"]
    assert service.conversation_allowed(key, "s-new")  # 1 of 3 used
    admin, csrf = as_user(app, "root@admin-test.invalid")
    admin.patch(f"/api/admin/tenants/{setup['a']['id']}", json={"trial_conversation_limit": 1}, headers=csrf)
    assert not service.conversation_allowed(key, "s-new")
    admin.patch(f"/api/admin/tenants/{setup['a']['id']}", json={"enabled": True}, headers=csrf)
    assert service.conversation_allowed(key, "s-new")


def test_inviting_a_user_returns_a_link_that_sets_the_password(app, setup):
    admin, csrf = as_user(app, "root@admin-test.invalid")
    res = admin.post(
        f"/api/admin/tenants/{setup['b']['id']}/users", json={"email": "New@Admin-Test.invalid"}, headers=csrf
    )
    assert res.status_code == 201
    link = res.get_json()["invite_link"]
    assert "/accept/?token=" in link
    token = link.split("token=")[1]
    guest = app.test_client()
    assert (
        guest.post("/api/auth/accept", json={"token": token, "new_password": "a good long password"}).status_code == 200
    )
    assert guest.get("/api/auth/me").get_json()["tenant"]["id"] == setup["b"]["id"]


def test_inviting_an_existing_email_is_a_409_and_bad_input_a_400_or_404(app, setup):
    admin, csrf = as_user(app, "root@admin-test.invalid")
    url = f"/api/admin/tenants/{setup['b']['id']}/users"
    assert admin.post(url, json={"email": "user-a@admin-test.invalid"}, headers=csrf).status_code == 409
    assert admin.post(url, json={"email": "nope"}, headers=csrf).status_code == 400
    assert (
        admin.post("/api/admin/tenants/999999/users", json={"email": "z@admin-test.invalid"}, headers=csrf).status_code
        == 404
    )


def test_reset_link_signs_the_user_out_when_used(app, setup):
    admin, csrf = as_user(app, "root@admin-test.invalid")
    victim, _ = as_user(app, "user-a@admin-test.invalid")
    uid = sql("SELECT id FROM users WHERE email = 'user-a@admin-test.invalid'")[0][0]
    link = admin.post(f"/api/admin/users/{uid}/reset-link", headers=csrf).get_json()["link"]
    assert victim.get("/api/auth/me").status_code == 200  # issuing a link changes nothing yet
    guest = app.test_client()
    assert (
        guest.post(
            "/api/auth/accept", json={"token": link.split("token=")[1], "new_password": "brand new password!"}
        ).status_code
        == 200
    )
    assert victim.get("/api/auth/me").status_code == 401
    assert admin.post("/api/admin/users/999999/reset-link", headers=csrf).status_code == 404


def test_moving_a_domain_moves_its_leads_and_the_trial_count(app, setup):
    admin, csrf = as_user(app, "root@admin-test.invalid")
    a_key, b = setup["a"]["key"], setup["b"]
    assert admin.patch(f"/api/admin/domains/{a_key}", json={"tenant_id": b["id"]}, headers=csrf).status_code == 200
    assert sql("SELECT DISTINCT tenant_id FROM domains WHERE key = %s", (a_key,)) == [(b["id"],)]
    leads = admin.get(f"/api/leads?tenant_id={b['id']}").get_json()["leads"]
    assert [lead["domain"] for lead in leads] == [a_key]


def test_moving_validates_its_input(app, setup):
    admin, csrf = as_user(app, "root@admin-test.invalid")
    key = setup["a"]["key"]
    assert admin.patch(f"/api/admin/domains/{key}", json={"tenant_id": "x"}, headers=csrf).status_code == 400
    assert admin.patch(f"/api/admin/domains/{key}", json={"tenant_id": 999999}, headers=csrf).status_code == 404
    assert (
        admin.patch("/api/admin/domains/NO_SUCH", json={"tenant_id": setup["b"]["id"]}, headers=csrf).status_code == 404
    )


def test_each_tenant_lists_its_websites_with_parent_and_www_alias(app, world, setup):
    a = setup["a"]
    sql("UPDATE domains SET address = %s WHERE key = %s", (f"{a['key'].lower()}.site.invalid", a["key"]))
    world.domain(a["id"], a["key"], f"www.{a['key'].lower()}.site.invalid")
    sql(
        "UPDATE domains SET parent = (SELECT id FROM domains WHERE key = 'COMMON' ORDER BY id LIMIT 1) WHERE key = %s",
        (a["key"],),
    )
    admin, _ = as_user(app, "root@admin-test.invalid")
    tenants = {t["id"]: t for t in admin.get("/api/admin/tenants").get_json()["tenants"]}
    mine, other = tenants[a["id"]], tenants[setup["b"]["id"]]
    assert mine["domain_count"] == 2 and mine["site_count"] == 1
    main, www = mine["domains"]
    assert main["address"].endswith(".site.invalid") and main["is_www_alias"] is False
    assert www["address"].startswith("www.") and www["is_www_alias"] is True
    assert main["parent_key"] == "COMMON" and main["parent_address"]
    # Another tenant's websites are never mixed in.
    assert {d["key"] for d in other["domains"]} == {setup["b"]["key"]}
