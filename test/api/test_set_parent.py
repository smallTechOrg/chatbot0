"""Setting a website's parent: tenants (own websites or COMMON) and admins (anything); no self-parent, no loops."""

import pytest
from conftest import sign_in

from chat import prompts
from core import db_pool


def sql(query, args=()):
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, args)
        return cur.fetchall() if cur.description else None


def as_user(app, email):
    client = app.test_client()
    return client, {"X-CSRF-Token": sign_in(client, email)}


@pytest.fixture
def setup(world):
    a, b = world.tenant("PA"), world.tenant("PB", enabled=False)
    world.domain(a["id"], a["key"] + "_2")  # a second website of A
    world.domain(a["id"], a["key"], f"www.{a['key'].lower()}.invalid")  # A's www alias shares A's key
    other = world.tenant("PC")
    world.user(a["id"], "owner-a@parent-test.invalid")
    world.user(b["id"], "owner-b@parent-test.invalid")
    world.user(other["id"], "owner-c@parent-test.invalid")
    world.user(a["id"], "root@parent-test.invalid", is_admin=True)
    return {"a": a["key"], "a2": a["key"] + "_2", "b": b["key"], "c": other["key"], "a_id": a["id"]}


def parent_keys(key):
    return sql(
        "SELECT d.address, p.key FROM domains d LEFT JOIN domains p ON p.id = d.parent WHERE d.key = %s ORDER BY d.id",
        (key,),
    )


def put(client, csrf, key, parent, admin=False):
    base = "/api/admin/domains" if admin else "/api/domains"
    return client.put(f"{base}/{key}/parent", json={"parent_key": parent}, headers=csrf)


def test_a_tenant_sets_its_website_under_another_of_its_own_and_the_chain_updates(app, setup):
    client, csrf = as_user(app, "owner-a@parent-test.invalid")
    res = put(client, csrf, setup["a2"], setup["a"])
    assert res.status_code == 200, res.get_json()
    assert res.get_json()["chain"]["chain"] == [setup["a2"], setup["a"]]
    # The prompt-chain view and the bot's own lookup agree straight away.
    assert client.get(f"/api/domains/{setup['a2']}/prompt-chain").get_json()["chain"] == [setup["a2"], setup["a"]]
    assert prompts.parent_chain(setup["a2"]) == [setup["a2"], setup["a"]]
    # And back to COMMON.
    assert put(client, csrf, setup["a2"], "COMMON").status_code == 200
    assert prompts.parent_chain(setup["a2"]) == [setup["a2"], "COMMON"]


def test_every_row_of_the_key_changes_together(app, setup):
    client, csrf = as_user(app, "owner-a@parent-test.invalid")
    assert put(client, csrf, setup["a"], setup["a2"]).status_code == 200
    rows = parent_keys(setup["a"])
    assert len(rows) == 2 and {p for _, p in rows} == {setup["a2"]}
    # The parent row is the main row, never the www alias.
    pid = sql("SELECT parent FROM domains WHERE key = %s LIMIT 1", (setup["a"],))[0][0]
    assert not sql("SELECT address FROM domains WHERE id = %s", (pid,))[0][0].startswith("www.")


def test_a_tenant_cannot_use_another_tenants_website_as_parent(app, setup):
    client, csrf = as_user(app, "owner-a@parent-test.invalid")
    before = parent_keys(setup["a2"])
    res = put(client, csrf, setup["a2"], setup["c"])
    assert res.status_code == 400 and "your own" in res.get_json()["error"]
    assert parent_keys(setup["a2"]) == before


def test_a_tenant_cannot_change_another_tenants_website_or_a_missing_one(app, setup):
    client, csrf = as_user(app, "owner-a@parent-test.invalid")
    assert put(client, csrf, setup["c"], setup["a"]).status_code == 403
    assert put(client, csrf, "NO_SUCH_KEY", setup["a"]).status_code == 404
    assert put(client, csrf, setup["a2"], "NO_SUCH_KEY").status_code == 400
    assert put(client, csrf, setup["a2"], "").status_code == 400
    assert put(client, csrf, setup["a2"], None).status_code == 400


def test_a_tenant_that_is_not_enabled_cannot_change_the_hierarchy(app, setup, world):
    world.domain(sql("SELECT tenant_id FROM domains WHERE key = %s LIMIT 1", (setup["b"],))[0][0], setup["b"] + "_2")
    client, csrf = as_user(app, "owner-b@parent-test.invalid")
    assert put(client, csrf, setup["b"] + "_2", setup["b"]).status_code == 403


def test_self_parenting_and_loops_are_rejected(app, setup):
    client, csrf = as_user(app, "owner-a@parent-test.invalid")
    res = put(client, csrf, setup["a"], setup["a"])
    assert res.status_code == 400 and "own parent" in res.get_json()["error"]
    assert put(client, csrf, setup["a2"], setup["a"]).status_code == 200  # A2 under A
    res = put(client, csrf, setup["a"], setup["a2"])  # A under A2 would loop
    assert res.status_code == 400 and "loop" in res.get_json()["error"]
    assert prompts.parent_chain(setup["a2"]) == [setup["a2"], setup["a"]]


def test_a_longer_loop_is_rejected_too(app, setup, world):
    third = setup["a"] + "_3"
    world.domain(setup["a_id"], third)
    client, csrf = as_user(app, "owner-a@parent-test.invalid")
    assert put(client, csrf, setup["a2"], setup["a"]).status_code == 200
    assert put(client, csrf, third, setup["a2"]).status_code == 200
    assert put(client, csrf, setup["a"], third).status_code == 400


def test_an_admin_sets_any_website_under_any_website(app, setup):
    client, csrf = as_user(app, "root@parent-test.invalid")
    res = put(client, csrf, setup["c"], setup["a"], admin=True)  # another tenant's website: fine for an admin
    assert res.status_code == 200 and res.get_json()["chain"]["chain"][:2] == [setup["c"], setup["a"]]
    assert put(client, csrf, setup["c"], setup["c"], admin=True).status_code == 400
    assert put(client, csrf, setup["a"], setup["c"], admin=True).status_code == 400  # loop
    assert put(client, csrf, "NO_SUCH_KEY", setup["a"], admin=True).status_code == 404


def test_the_admin_endpoint_is_admin_only_and_needs_csrf(app, setup):
    client, csrf = as_user(app, "owner-a@parent-test.invalid")
    assert put(client, csrf, setup["a2"], setup["a"], admin=True).status_code == 403
    admin, _ = as_user(app, "root@parent-test.invalid")
    assert admin.put(f"/api/admin/domains/{setup['a2']}/parent", json={"parent_key": setup["a"]}).status_code == 403
    assert app.test_client().put(f"/api/domains/{setup['a2']}/parent", json={"parent_key": "COMMON"}).status_code == 401


def test_the_site_list_carries_each_websites_parent(app, setup):
    client, csrf = as_user(app, "owner-a@parent-test.invalid")
    put(client, csrf, setup["a2"], setup["a"])
    listed = {d["key"]: d for d in client.get("/api/domains").get_json()["domains"]}
    assert listed[setup["a2"]]["parent_key"] == setup["a"]
