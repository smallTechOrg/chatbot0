"""The trial cap: a tenant that is not enabled answers a limited number of conversations, with no LLM call after."""

import pytest

from api import chat as chat_api
from tenancy import service


@pytest.fixture
def llm_calls(monkeypatch):
    calls = []

    def reply(text, session_id, request_type, domain):
        calls.append(session_id)
        return "llm reply"

    monkeypatch.setattr(chat_api, "get_groq_response", reply)
    return calls


def test_enabled_tenants_are_never_capped(world):
    t = world.tenant("Enabled", enabled=True, limit=1)
    for _ in range(3):
        world.lead(t["key"])
    assert service.conversation_allowed(t["key"], "brand-new-session")


def test_a_disabled_tenant_is_allowed_until_it_reaches_its_limit(world):
    t = world.tenant("Trial", enabled=False, limit=2)
    assert service.conversation_allowed(t["key"], "s-new")
    world.lead(t["key"])
    assert service.conversation_allowed(t["key"], "s-new")
    world.lead(t["key"])
    assert not service.conversation_allowed(t["key"], "s-new")


def test_a_started_conversation_continues_past_the_limit(world):
    t = world.tenant("Trial", enabled=False, limit=1)
    started = world.lead(t["key"])
    world.lead(t["key"])
    assert service.conversation_allowed(t["key"], started)


def test_the_count_spans_all_of_the_tenants_domains_and_only_its_own(world):
    a, b = world.tenant("A", enabled=False, limit=2), world.tenant("B", enabled=False, limit=2)
    world.domain(a["id"], a["key"] + "_2")
    world.lead(a["key"])
    world.lead(a["key"] + "_2")
    world.lead(b["key"])
    assert not service.conversation_allowed(a["key"], "new")
    assert service.conversation_allowed(b["key"], "new")


def test_a_domain_no_tenant_owns_is_not_capped():
    assert service.conversation_allowed("NO_SUCH_DOMAIN_KEY", "s")


def test_the_www_row_shares_the_tenant_of_its_key(world):
    t = world.tenant("Trial", enabled=False, limit=1)
    world.domain(t["id"], t["key"])  # a second row with the same key, like the www row
    world.lead(t["key"])
    assert not service.conversation_allowed(t["key"], "new")


def post_chat(client, domain_address, session_id):
    return client.post(
        f"/chat?origin=https://{domain_address}",
        json={"input": "hi", "session_id": session_id, "request_type": "sales"},
    )


def address(world, t):
    return f"{t['key'].lower()}.invalid"


def test_chat_over_the_cap_replies_without_calling_the_llm(client, world, llm_calls):
    t = world.tenant("Trial", enabled=False, limit=1)
    world.lead(t["key"])
    res = post_chat(client, address(world, t), "00000000-0000-4000-8000-0000000000aa")
    assert res.status_code == 200
    body = res.get_json()
    assert body["success"] is True and body["response"] == service.TRIAL_LIMIT_REPLY
    assert llm_calls == []


def test_chat_under_the_cap_calls_the_llm(client, world, llm_calls):
    t = world.tenant("Trial", enabled=False, limit=5)
    res = post_chat(client, address(world, t), "00000000-0000-4000-8000-0000000000bb")
    assert res.get_json()["response"] == "llm reply"
    assert len(llm_calls) == 1


def test_chat_for_an_enabled_tenant_is_unchanged(client, world, llm_calls):
    t = world.tenant("Live", enabled=True, limit=0)
    assert (
        post_chat(client, address(world, t), "00000000-0000-4000-8000-0000000000cc").get_json()["response"]
        == "llm reply"
    )
