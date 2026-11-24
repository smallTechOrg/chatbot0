"""Per-tenant Slack delivery: a tenant's webhook gets its own leads' summaries and never another tenant's."""

from datetime import UTC, datetime

import pytest

from core import config, crypto
from summary import periodic, slack, tenant_slack
from tenancy import repository

HOOK_A = "https://hooks.slack.com/services/TA/BA/aaaa"
HOOK_B = "https://hooks.slack.com/services/TB/BB/bbbb"


@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "unit-test-secret-key")
    monkeypatch.setattr(slack.config, "environment_label", lambda: None)


@pytest.fixture
def posts(monkeypatch):
    seen = []
    monkeypatch.setattr(tenant_slack, "post_to_slack", lambda payload, url=None: seen.append((url, payload["text"])))
    return seen


def _session(domain, name, **extra):
    return {
        "session_id": f"s-{name}",
        "domain": domain,
        "name": name,
        "summary": f"{name} wants a quote",
        "first_message": datetime(2026, 10, 7, 10, 43, tzinfo=UTC),
        **extra,
    }


def _result(*sessions):
    return {"run_at": datetime(2026, 10, 7, 12, 0, tzinfo=UTC), "sessions": list(sessions)}


def _with_hook(tenant, url):
    repository.set_slack_webhook(tenant["id"], crypto.encrypt(url))


def test_each_tenant_gets_only_its_own_leads(world, posts):
    a, b = world.tenant("A"), world.tenant("B")
    _with_hook(a, HOOK_A)
    _with_hook(b, HOOK_B)
    result = _result(_session(a["key"], "Alice"), _session(b["key"], "Bob"))

    sent = tenant_slack.send_tenant_summaries(result)

    assert sent == {a["id"]: 1, b["id"]: 1}
    by_url = dict(posts)
    assert "Alice" in by_url[HOOK_A] and "Bob" not in by_url[HOOK_A]
    assert "Bob" in by_url[HOOK_B] and "Alice" not in by_url[HOOK_B]


def test_the_format_is_the_same_as_the_global_message(world, posts):
    a = world.tenant("A")
    _with_hook(a, HOOK_A)
    session = _session(a["key"], "Alice")
    tenant_slack.send_tenant_summaries(_result(session))
    [expected] = slack.build_messages(_result(session))
    assert posts == [(HOOK_A, expected["text"])]


def test_a_tenant_without_a_webhook_gets_nothing_and_others_are_unaffected(world, posts):
    a, b = world.tenant("A"), world.tenant("B")
    _with_hook(b, HOOK_B)
    tenant_slack.send_tenant_summaries(_result(_session(a["key"], "Alice"), _session(b["key"], "Bob")))
    assert [url for url, _ in posts] == [HOOK_B]


def test_resent_summaries_are_not_sent_to_tenants_again(world, posts):
    a = world.tenant("A")
    _with_hook(a, HOOK_A)
    assert tenant_slack.send_tenant_summaries(_result(_session(a["key"], "Alice", resent=True))) == {}
    assert posts == []


def test_a_failing_tenant_webhook_does_not_stop_the_others(world, monkeypatch):
    a, b = world.tenant("A"), world.tenant("B")
    _with_hook(a, HOOK_A)
    _with_hook(b, HOOK_B)
    seen = []

    def post(payload, url=None):
        if url == HOOK_A:
            raise ConnectionError(f"unreachable {url}")
        seen.append(url)

    monkeypatch.setattr(tenant_slack, "post_to_slack", post)
    sent = tenant_slack.send_tenant_summaries(_result(_session(a["key"], "Alice"), _session(b["key"], "Bob")))
    assert seen == [HOOK_B] and sent == {b["id"]: 1}


def test_an_unreadable_webhook_is_skipped(world, posts, monkeypatch):
    a = world.tenant("A")
    _with_hook(a, HOOK_A)
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "a-different-key")
    assert tenant_slack.send_tenant_summaries(_result(_session(a["key"], "Alice"))) == {}
    assert posts == []


def test_unknown_domains_and_empty_runs_send_nothing(posts):
    assert tenant_slack.send_tenant_summaries(_result(_session("NO_SUCH_KEY", "X"))) == {}
    assert tenant_slack.send_tenant_summaries(_result()) == {}
    assert posts == []


def test_the_periodic_run_still_sends_everything_to_the_global_channel(world, posts, monkeypatch):
    a = world.tenant("A")
    _with_hook(a, HOOK_A)
    global_runs = []
    monkeypatch.setattr(periodic, "find_chats_needing_summary", lambda: [_session(a["key"], "Alice")])
    monkeypatch.setattr(periodic, "fetch_full_conversation_history", lambda sid: [{"type": "human", "content": "hi"}])
    monkeypatch.setattr(periodic, "summarise_conversation", lambda conv: "wants a quote")
    monkeypatch.setattr(periodic, "save_summary", lambda sid, summary: None)
    monkeypatch.setattr(periodic, "find_unnotified_summaries", lambda: [])
    monkeypatch.setattr(periodic, "mark_summaries_notified", lambda ids: len(ids))
    monkeypatch.setattr(periodic, "send_summaries_to_slack", lambda r: global_runs.append(r) or {"sent": 1})

    result = periodic.periodic_summary()

    assert len(global_runs) == 1 and result["slack"] == {"sent": 1}
    assert result["tenant_slack"] == {a["id"]: 1}
    assert [url for url, _ in posts] == [HOOK_A]
