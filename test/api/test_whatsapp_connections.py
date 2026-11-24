"""/api/whatsapp/connections: a tenant manages the numbers of its own websites once enabled; admins manage all."""

import uuid

import pytest
from conftest import sign_in

from core import config, db_pool
from whatsapp import management
from whatsapp.client import GraphResult

TOKEN, SECRET = "EAAtoken123", "app-secret-1"


@pytest.fixture(autouse=True)
def graph(monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "unit-test-secret-key")
    state = {"check": GraphResult(True, {"display_phone_number": "+1 555 0100", "verified_name": "Acme"}), "sent": []}
    monkeypatch.setattr(management, "check_number", lambda pnid, token: state["check"])

    def fake_send(pnid, token, to, body):
        state["sent"].append((to, body))
        return state.get("send", GraphResult(True, {}))

    monkeypatch.setattr(management, "send_text", fake_send)
    return state


@pytest.fixture
def setup(world):
    a, b = world.tenant("A"), world.tenant("B")
    world.user(a["id"], "a@wa-test.invalid")
    world.user(b["id"], "b@wa-test.invalid")
    off = world.tenant("Off", enabled=False)
    world.user(off["id"], "off@wa-test.invalid")
    world.user(a["id"], "root@wa-test.invalid", is_admin=True)
    yield {"a": a, "b": b, "off": off}
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM whatsapp_connections WHERE domain_key = ANY(%s)", ([a["key"], b["key"], off["key"]],))


def as_user(app, email):
    client = app.test_client()
    return client, {"X-CSRF-Token": sign_in(client, email)}


def new_number():
    return str(uuid.uuid4().int)[:15]


def connect(client, csrf, key, number=None, **extra):
    body = {
        "phone_number_id": number or new_number(),
        "domain_key": key,
        "access_token": TOKEN,
        "app_secret": SECRET,
    } | extra
    return client.post("/api/whatsapp/connections", json=body, headers=csrf)


def test_an_enabled_tenant_connects_a_number_for_its_own_website(app, setup):
    client, csrf = as_user(app, "a@wa-test.invalid")
    res = connect(client, csrf, setup["a"]["key"])
    out = res.get_json()
    assert res.status_code == 201 and out["check"]["ok"] is True and out["check"]["verified_name"] == "Acme"
    c = out["connection"]
    assert c["webhook_url"].endswith(f"/whatsapp/webhook/{c['id']}") and c["verify_token"]
    assert "access_token" not in str(out) and TOKEN not in str(out) and SECRET not in str(out)


def test_ids_pasted_with_invisible_characters_are_cleaned(app, setup):
    client, csrf = as_user(app, "a@wa-test.invalid")
    number = new_number()
    res = connect(client, csrf, setup["a"]["key"], number=f"‎ID: {number[:8]} {number[8:]}")
    assert res.status_code == 201 and res.get_json()["connection"]["phone_number_id"] == number


def test_a_failed_token_check_is_reported_and_the_connection_needs_attention(app, setup, graph):
    graph["check"] = GraphResult(False, None, "HTTP 401: bad token", 190)
    client, csrf = as_user(app, "a@wa-test.invalid")
    out = connect(client, csrf, setup["a"]["key"]).get_json()
    assert out["check"] == {"ok": False, "error": "HTTP 401: bad token"}
    shown = client.get(f"/api/whatsapp/connections/{out['connection']['id']}").get_json()["connection"]
    assert shown["status"] == "needs_attention"


def test_a_tenant_cannot_connect_a_number_to_another_tenants_website(app, setup):
    client, csrf = as_user(app, "a@wa-test.invalid")
    assert connect(client, csrf, setup["b"]["key"]).status_code == 403


def test_a_tenant_not_enabled_yet_can_look_but_not_change(app, setup):
    client, csrf = as_user(app, "off@wa-test.invalid")
    assert client.get("/api/whatsapp/connections").get_json()["connections"] == []
    assert connect(client, csrf, setup["off"]["key"]).status_code == 403


def test_tenants_only_see_their_own_connections(app, setup):
    a, csrf_a = as_user(app, "a@wa-test.invalid")
    b, csrf_b = as_user(app, "b@wa-test.invalid")
    cid = connect(a, csrf_a, setup["a"]["key"]).get_json()["connection"]["id"]
    assert [c["id"] for c in a.get("/api/whatsapp/connections").get_json()["connections"]] == [cid]
    assert b.get("/api/whatsapp/connections").get_json()["connections"] == []
    assert b.get(f"/api/whatsapp/connections/{cid}").status_code == 403
    assert b.patch(f"/api/whatsapp/connections/{cid}", json={"access_token": "x"}, headers=csrf_b).status_code == 403
    assert b.post(f"/api/whatsapp/connections/{cid}/check", headers=csrf_b).status_code == 403
    assert (
        b.post(f"/api/whatsapp/connections/{cid}/test", json={"to": "919876543210"}, headers=csrf_b).status_code == 403
    )
    admin, _ = as_user(app, "root@wa-test.invalid")
    assert cid in [c["id"] for c in admin.get("/api/whatsapp/connections").get_json()["connections"]]
    assert admin.get(f"/api/whatsapp/connections/{cid}").status_code == 200


def test_a_number_can_only_be_connected_once_and_input_is_validated(app, setup):
    client, csrf = as_user(app, "a@wa-test.invalid")
    number = new_number()
    assert connect(client, csrf, setup["a"]["key"], number=number).status_code == 201
    assert connect(client, csrf, setup["a"]["key"], number=number).status_code == 409
    assert connect(client, csrf, setup["a"]["key"], number="12ab").status_code == 400
    assert connect(client, csrf, setup["a"]["key"], access_token="").status_code == 400
    admin, acsrf = as_user(app, "root@wa-test.invalid")
    assert connect(admin, acsrf, "NO_SUCH_KEY").status_code == 404


def test_connections_need_a_session_and_csrf(app, client, setup):
    assert client.get("/api/whatsapp/connections").status_code == 401
    a, _ = as_user(app, "a@wa-test.invalid")
    body = {
        "phone_number_id": new_number(),
        "domain_key": setup["a"]["key"],
        "access_token": TOKEN,
        "app_secret": SECRET,
    }
    assert a.post("/api/whatsapp/connections", json=body).status_code == 403


def test_replacing_credentials_rechecks_the_token(app, setup, graph):
    client, csrf = as_user(app, "a@wa-test.invalid")
    cid = connect(client, csrf, setup["a"]["key"]).get_json()["connection"]["id"]
    graph["check"] = GraphResult(True, {"display_phone_number": "+1 555 0199", "verified_name": "Acme Inc"})
    res = client.patch(f"/api/whatsapp/connections/{cid}", json={"access_token": "EAAnew"}, headers=csrf)
    assert res.get_json()["check"]["verified_name"] == "Acme Inc"
    assert client.patch(f"/api/whatsapp/connections/{cid}", json={}, headers=csrf).status_code == 400
    other = client.patch(f"/api/whatsapp/connections/{cid}", json={"domain_key": setup["b"]["key"]}, headers=csrf)
    assert other.status_code == 403


def test_check_and_test_message(app, setup, graph):
    client, csrf = as_user(app, "a@wa-test.invalid")
    cid = connect(client, csrf, setup["a"]["key"]).get_json()["connection"]["id"]
    assert client.post(f"/api/whatsapp/connections/{cid}/check", headers=csrf).get_json()["check"]["ok"] is True
    sent = client.post(f"/api/whatsapp/connections/{cid}/test", json={"to": "+91 98765-43210"}, headers=csrf).get_json()
    assert sent["result"] == {"ok": True, "to": "+919876543210"}
    assert graph["sent"] == [("919876543210", management.DEFAULT_TEST_BODY)]
    assert client.post(f"/api/whatsapp/connections/{cid}/test", json={"to": "abc"}, headers=csrf).status_code == 400


def test_a_failed_test_message_comes_with_a_hint(app, setup, graph):
    client, csrf = as_user(app, "a@wa-test.invalid")
    cid = connect(client, csrf, setup["a"]["key"]).get_json()["connection"]["id"]
    graph["send"] = GraphResult(False, None, "token expired", 190)
    res = client.post(f"/api/whatsapp/connections/{cid}/test", json={"to": "919876543210"}, headers=csrf).get_json()[
        "result"
    ]
    assert res["ok"] is False and "expired" in res["hint"]
    assert client.get(f"/api/whatsapp/connections/{cid}").get_json()["connection"]["status"] == "needs_attention"


def test_unknown_connection_is_404(app, setup):
    client, _ = as_user(app, "a@wa-test.invalid")
    assert client.get("/api/whatsapp/connections/nope").status_code == 404


@pytest.mark.parametrize(
    "pasted",
    ["\u200e{}\u200f", "\u00a0{} ", "ID: {}", "Phone number ID: {}", "\ufeff{}\u200b", "{}\n"],
)
def test_pasted_id_and_credentials_with_invisible_characters_are_cleaned(app, setup, pasted):
    from whatsapp import repository

    client, csrf = as_user(app, "a@wa-test.invalid")
    pnid = new_number()
    res = connect(
        client, csrf, setup["a"]["key"], number=pasted.format(pnid), access_token="\u200etok ", app_secret=" sec\u00a0"
    )
    assert res.status_code == 201, res.get_json()
    full = repository.get_connection_by_number(pnid)
    assert (full["access_token"], full["app_secret"]) == ("tok", "sec")


def test_a_phone_number_instead_of_the_id_is_explained(app, setup):
    client, csrf = as_user(app, "a@wa-test.invalid")
    res = connect(client, csrf, setup["a"]["key"], number="+1 555 0100")
    assert res.status_code == 400
    error = res.get_json()["error"]
    assert "numeric ID" in error and "Received 11 characters" in error


def test_a_test_message_outside_the_24_hour_window_comes_with_a_hint(app, setup, graph):
    client, csrf = as_user(app, "a@wa-test.invalid")
    cid = connect(client, csrf, setup["a"]["key"]).get_json()["connection"]["id"]
    graph["send"] = GraphResult(False, None, "HTTP 400: Re-engagement message", 131047)
    result = client.post(f"/api/whatsapp/connections/{cid}/test", json={"to": "919876543210"}, headers=csrf).get_json()[
        "result"
    ]
    assert "last 24 hours" in result["hint"]


def test_the_connection_pages_are_off_without_accounts(app, client, monkeypatch):
    monkeypatch.setattr(app, "secret_key", None)
    assert client.get("/api/whatsapp/connections").status_code == 401  # no session can exist without a key
