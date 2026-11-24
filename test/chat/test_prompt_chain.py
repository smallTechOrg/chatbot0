"""Prompts resolve up the whole parent chain (cycle-safe), and the chain API reports where each one comes from."""

import uuid

import pytest
from conftest import sign_in

from chat import prompt_chain, prompts
from core import db_pool


def sql(query, args=()):
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, args)
        return cur.fetchall() if cur.description else None


@pytest.fixture
def family(world):
    """Four generations: COMMON <- PARENT <- GRAND <- GREAT (all owned by one tenant). Prompt rows are removed after."""
    t = world.tenant("Fam")
    suffix = uuid.uuid4().hex[:6].upper()
    keys = {n: f"{n}_{suffix}" for n in ("PARENT", "GRAND", "GREAT")}
    for key in keys.values():
        world.domain(t["id"], key)
    ids = {k: sql("SELECT id FROM domains WHERE key = %s ORDER BY id LIMIT 1", (k,))[0][0] for k in keys.values()}
    common = sql("SELECT id FROM domains WHERE key = 'COMMON' ORDER BY id LIMIT 1")[0][0]
    sql("UPDATE domains SET parent = %s WHERE id = %s", (common, ids[keys["PARENT"]]))
    sql("UPDATE domains SET parent = %s WHERE id = %s", (ids[keys["PARENT"]], ids[keys["GRAND"]]))
    sql("UPDATE domains SET parent = %s WHERE id = %s", (ids[keys["GRAND"]], ids[keys["GREAT"]]))
    yield {"tenant": t, "ids": ids, **keys}
    sql("DELETE FROM prompts WHERE domain = ANY(%s)", ([*keys.values(), t["key"]],))


def put(domain, agent, kind, text):
    sql(
        "INSERT INTO prompts (domain, agent_type, type, text) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (domain, agent_type, type) DO UPDATE SET text = EXCLUDED.text",
        (domain, agent, kind, text),
    )


def test_the_chain_walks_every_level(family):
    assert prompts.parent_chain(family["GREAT"]) == [family["GREAT"], family["GRAND"], family["PARENT"], "COMMON"]
    assert prompts.parent_chain("COMMON") == ["COMMON"]


def test_a_prompt_is_inherited_from_a_grandparent_not_only_the_parent(family):
    put(family["PARENT"], "sales", "company", "from the parent")
    text, source = prompts.resolve_prompt(family["GREAT"], "sales", "company")
    assert (text, source) == ("from the parent", family["PARENT"])
    assert prompts.load_prompt_from_db(family["GREAT"], "sales", "company") == "from the parent"


def test_the_nearest_prompt_wins(family):
    put(family["PARENT"], "sales", "company", "parent text")
    put(family["GRAND"], "sales", "company", "grand text")
    assert prompts.resolve_prompt(family["GREAT"], "sales", "company") == ("grand text", family["GRAND"])
    put(family["GREAT"], "sales", "company", "own text")
    assert prompts.resolve_prompt(family["GREAT"], "sales", "company") == ("own text", family["GREAT"])


def test_a_prompt_missing_everywhere_is_none(family):
    assert prompts.resolve_prompt(family["GREAT"], "sales", "no-such-type") == (None, None)


def test_a_parent_loop_cannot_hang_the_lookup(family):
    ids = family["ids"]
    sql("UPDATE domains SET parent = %s WHERE id = %s", (ids[family["GREAT"]], ids[family["PARENT"]]))  # a loop
    chain = prompts.parent_chain(family["GREAT"])
    assert chain == [family["GREAT"], family["GRAND"], family["PARENT"]]
    assert prompts.resolve_prompt(family["GREAT"], "sales", "no-such-type") == (None, None)


def test_describe_labels_own_inherited_default_and_missing(family):
    put(family["GREAT"], "sales", "company", "own company text")
    put(family["GRAND"], "sales", "base-prompt", "x" * 500)
    d = prompt_chain.describe(family["GREAT"])
    assert d["chain"][-1] == "COMMON" and d["ends_at_default"] is True
    by_type = {(p["agent_type"], p["type"]): p for p in d["prompts"]}
    assert len(by_type) == len(prompt_chain.USED_PROMPTS) == 6
    assert (by_type["sales", "company"]["origin"], by_type["sales", "company"]["label"]) == ("own", "own")
    base = by_type["sales", "base-prompt"]
    assert base["label"] == f"inherited from {family['GRAND']}" and base["source"] == family["GRAND"]
    assert len(base["preview"]) <= prompt_chain.PREVIEW_CHARS and base["preview"].endswith("…")
    intro = by_type["sales", "intro-message"]  # only COMMON has it
    assert (intro["origin"], intro["label"]) == ("default", "default (COMMON)")
    assert intro["preview"]


def test_describe_reports_a_prompt_that_exists_nowhere(family, monkeypatch):
    monkeypatch.setattr(prompt_chain, "USED_PROMPTS", (("sales", "no-such-type"),))
    [only] = prompt_chain.describe(family["GREAT"])["prompts"]
    assert only["origin"] == "missing" and only["source"] is None


def _client_for(app, world, tenant, admin=False):
    email = f"u{uuid.uuid4().hex[:6]}@chain.test"
    world.user(tenant["id"], email, is_admin=admin)
    client = app.test_client()
    sign_in(client, email)
    return client


def test_the_api_serves_own_websites_to_tenants_and_any_to_admins(app, world, family):
    own = family["tenant"]
    stranger = world.tenant("Stranger")
    owner = _client_for(app, world, own)
    res = owner.get(f"/api/domains/{family['GREAT']}/prompt-chain")
    assert res.status_code == 200 and res.get_json()["chain"][0] == family["GREAT"]
    other = _client_for(app, world, stranger)
    assert other.get(f"/api/domains/{family['GREAT']}/prompt-chain").status_code == 403
    admin = _client_for(app, world, stranger, admin=True)
    assert admin.get(f"/api/domains/{family['GREAT']}/prompt-chain").status_code == 200
    assert admin.get("/api/domains/NO_SUCH_KEY/prompt-chain").status_code == 404


def test_the_api_needs_a_session(client):
    assert client.get("/api/domains/COMMON/prompt-chain").status_code == 401


def test_the_sites_prompt_editor_sees_the_inherited_text_from_the_whole_chain(app, world, family):
    put(family["PARENT"], "sales", "company", "grandparent text")
    owner = _client_for(app, world, family["tenant"])
    prompts_json = owner.get(f"/api/domains/{family['GREAT']}/prompts").get_json()["prompts"]
    assert prompts_json["company"] == {"text": "grandparent text", "own": False}
