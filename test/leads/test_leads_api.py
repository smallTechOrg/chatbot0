"""/api/leads*: a tenant reaches its own leads and nobody else's; admins reach all."""

import pytest
from conftest import sign_in

from leads import service


@pytest.fixture
def two_tenants(world):
    a, b = world.tenant("A"), world.tenant("B")
    users = {
        "a": world.user(a["id"], "a@tenant-a.invalid"),
        "b": world.user(b["id"], "b@tenant-b.invalid"),
        "admin": world.user(a["id"], "root@tenant-a.invalid", is_admin=True),
    }
    leads = {"a": world.lead(a["key"], "Alice"), "b": world.lead(b["key"], "Bob")}
    return {"a": a, "b": b, "users": users, "leads": leads}


def client_for(app, email):
    client = app.test_client()
    return client, sign_in(client, email)


def names(res):
    return sorted(lead["name"] for lead in res.get_json()["leads"])


# ---------------------------------------------------------------- reading


def test_a_tenant_sees_only_its_own_leads(app, two_tenants):
    a, _ = client_for(app, "a@tenant-a.invalid")
    b, _ = client_for(app, "b@tenant-b.invalid")
    assert names(a.get("/api/leads")) == ["Alice"]
    assert names(b.get("/api/leads")) == ["Bob"]


def test_leads_carry_channel_domain_and_tenant(app, two_tenants):
    a, _ = client_for(app, "a@tenant-a.invalid")
    lead = a.get("/api/leads").get_json()["leads"][0]
    assert lead["channel"] == "web" and lead["domain"] == two_tenants["a"]["key"]
    assert lead["tenant_id"] == two_tenants["a"]["id"] and lead["tenant"].startswith("A-")
    assert {"session_id", "email", "mobile_number", "status", "remarks", "summary", "time"} <= lead.keys()


def test_a_tenant_cannot_ask_for_another_tenants_leads_by_id(app, two_tenants):
    b, _ = client_for(app, "b@tenant-b.invalid")
    assert b.get(f"/api/leads?tenant_id={two_tenants['a']['id']}").status_code == 403
    assert names(b.get(f"/api/leads?tenant_id={two_tenants['b']['id']}")) == ["Bob"]


def test_an_admin_sees_every_lead_or_one_tenants(app, two_tenants):
    admin, _ = client_for(app, "root@tenant-a.invalid")
    assert {"Alice", "Bob"} <= set(names(admin.get("/api/leads")))
    assert names(admin.get(f"/api/leads?tenant_id={two_tenants['b']['id']}")) == ["Bob"]


def test_bad_tenant_id_is_a_400(app, two_tenants):
    admin, _ = client_for(app, "root@tenant-a.invalid")
    assert admin.get("/api/leads?tenant_id=abc").status_code == 400


def test_everything_needs_a_session(client, two_tenants):
    sid = two_tenants["leads"]["a"]
    assert client.get("/api/leads").status_code == 401
    assert client.patch(f"/api/leads/{sid}", json={"status": "CLOSED"}).status_code == 401
    assert client.get(f"/api/leads/{sid}/history").status_code == 401


# ---------------------------------------------------------------- history


def test_a_tenant_reads_its_lead_history_but_not_anothers(app, two_tenants):
    a, _ = client_for(app, "a@tenant-a.invalid")
    own = a.get(f"/api/leads/{two_tenants['leads']['a']}/history")
    assert own.status_code == 200
    assert [m["content"] for m in own.get_json()["history"]] == ["hello from Alice"]
    assert a.get(f"/api/leads/{two_tenants['leads']['b']}/history").status_code == 403


def test_reading_history_never_adds_the_intro_message(app, world, two_tenants):
    from chat.history import get_session_history

    empty = world.lead(two_tenants["a"]["key"], "Quiet")
    get_session_history(empty).clear()
    a, _ = client_for(app, "a@tenant-a.invalid")
    assert a.get(f"/api/leads/{empty}/history").get_json() == {"history": []}
    assert get_session_history(empty).get_messages() == []


def test_unknown_lead_is_a_404(app, two_tenants):
    a, _ = client_for(app, "a@tenant-a.invalid")
    assert a.get("/api/leads/00000000-0000-0000-0000-000000000000/history").status_code == 404


# ---------------------------------------------------------------- patching


def lead_row(sid):
    from core import db_pool

    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT status, remarks, is_active FROM chat_info WHERE session_id = %s", (sid,))
        return cur.fetchone()


def test_a_tenant_updates_its_own_lead(app, two_tenants):
    a, csrf = client_for(app, "a@tenant-a.invalid")
    sid = two_tenants["leads"]["a"]
    res = a.patch(f"/api/leads/{sid}", json={"status": "CLOSED", "remarks": "called"}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200
    assert lead_row(sid) == ("CLOSED", "called", True)


def test_a_tenant_cannot_patch_another_tenants_lead(app, two_tenants):
    b, csrf = client_for(app, "b@tenant-b.invalid")
    sid = two_tenants["leads"]["a"]
    res = b.patch(
        f"/api/leads/{sid}",
        json={"status": "CLOSED", "remarks": "mine now", "is_active": False},
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 403
    assert lead_row(sid)[0] != "CLOSED" and lead_row(sid)[1] is None and lead_row(sid)[2] is True


def test_an_admin_can_patch_any_lead(app, two_tenants):
    admin, csrf = client_for(app, "root@tenant-a.invalid")
    sid = two_tenants["leads"]["b"]
    assert (
        admin.patch(f"/api/leads/{sid}", json={"is_active": False}, headers={"X-CSRF-Token": csrf}).status_code == 200
    )
    assert lead_row(sid)[2] is False


def test_patch_needs_the_csrf_token(app, two_tenants):
    a, _ = client_for(app, "a@tenant-a.invalid")
    sid = two_tenants["leads"]["a"]
    assert a.patch(f"/api/leads/{sid}", json={"status": "CLOSED"}).status_code == 403
    assert lead_row(sid)[0] != "CLOSED"


@pytest.mark.parametrize(
    "body",
    [{}, {"status": "NOPE"}, {"remarks": 5}, {"remarks": "x" * 5001}, {"is_active": "yes"}],
)
def test_patch_validates_its_input(app, two_tenants, body):
    a, csrf = client_for(app, "a@tenant-a.invalid")
    sid = two_tenants["leads"]["a"]
    assert a.patch(f"/api/leads/{sid}", json=body, headers={"X-CSRF-Token": csrf}).status_code == 400


def test_patching_an_unknown_lead_is_a_404(app, two_tenants):
    a, csrf = client_for(app, "a@tenant-a.invalid")
    res = a.patch("/api/leads/nope", json={"status": "OPEN"}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 404


def test_a_lead_on_a_domain_without_a_tenant_is_not_reachable_by_users(app, world, two_tenants):
    from core import db_pool

    orphan = world.lead(two_tenants["a"]["key"], "Orphan")
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("UPDATE chat_info SET domain = 'NO_SUCH_DOMAIN' WHERE session_id = %s", (orphan,))
    a, csrf = client_for(app, "a@tenant-a.invalid")
    assert "Orphan" not in names(a.get("/api/leads"))
    assert a.patch(f"/api/leads/{orphan}", json={"status": "CLOSED"}, headers={"X-CSRF-Token": csrf}).status_code == 403


def test_service_rules_without_http(two_tenants):
    user = {"is_admin": False, "tenant_id": two_tenants["a"]["id"]}
    with pytest.raises(service.LeadError):
        service.list_leads(user, two_tenants["b"]["id"])
