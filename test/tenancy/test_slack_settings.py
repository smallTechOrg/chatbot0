"""A tenant's own Slack webhook: stored encrypted, never shown back, test button, enabled tenants only."""

import pytest
from conftest import sign_in

from core import config, db_pool
from summary import slack
from tenancy import slack_settings

HOOK = "https://hooks.slack.com/services/T000/B000/secretsecret"


@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "unit-test-secret-key")


@pytest.fixture
def posts(monkeypatch):
    seen = []
    monkeypatch.setattr(slack, "post_to_slack", lambda payload, webhook_url=None: seen.append((webhook_url, payload)))
    return seen


def _signed_in(world, client, enabled=True):
    t = world.tenant("Acme", enabled=enabled)
    world.user(t["id"], f"owner{t['id']}@acme.test")
    csrf = sign_in(client, f"owner{t['id']}@acme.test")
    return t, {"X-CSRF-Token": csrf}


def _stored(tenant_id):
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT slack_webhook_enc FROM tenants WHERE id = %s", (tenant_id,))
        return cur.fetchone()[0]


def test_it_starts_not_set(world, client):
    _, h = _signed_in(world, client)
    assert client.get("/api/slack", headers=h).get_json() == {"configured": False, "enabled": True}


def test_saving_stores_it_encrypted_and_never_shows_it_back(world, client):
    t, h = _signed_in(world, client)
    res = client.put("/api/slack", json={"webhook_url": HOOK}, headers=h)
    assert res.status_code == 200 and HOOK not in res.get_data(as_text=True)
    stored = _stored(t["id"])
    assert stored and HOOK not in stored and "secretsecret" not in stored
    status = client.get("/api/slack", headers=h)
    assert status.get_json()["configured"] is True and "hooks.slack.com" not in status.get_data(as_text=True)
    assert slack_settings.webhook_for(t["id"]) == HOOK


@pytest.mark.parametrize(
    "bad", ["", "not a url", "http://hooks.slack.com/services/a/b/c", "https://evil.example/services/a", None, 5]
)
def test_only_slack_webhook_urls_are_accepted(world, client, bad):
    t, h = _signed_in(world, client)
    assert client.put("/api/slack", json={"webhook_url": bad}, headers=h).status_code == 422
    assert _stored(t["id"]) is None


def test_a_tenant_that_is_not_enabled_cannot_save_or_test(world, client):
    t, h = _signed_in(world, client, enabled=False)
    assert client.put("/api/slack", json={"webhook_url": HOOK}, headers=h).status_code == 403
    assert client.post("/api/slack/test", headers=h).status_code == 403
    assert _stored(t["id"]) is None


def test_clearing_removes_it(world, client):
    t, h = _signed_in(world, client)
    client.put("/api/slack", json={"webhook_url": HOOK}, headers=h)
    assert client.delete("/api/slack", headers=h).status_code == 200
    assert _stored(t["id"]) is None


def test_the_test_button_posts_to_the_tenants_own_webhook(world, client, posts):
    _, h = _signed_in(world, client)
    assert client.post("/api/slack/test", headers=h).status_code == 409  # nothing saved yet
    client.put("/api/slack", json={"webhook_url": HOOK}, headers=h)
    assert client.post("/api/slack/test", headers=h).status_code == 200
    assert [url for url, _ in posts] == [HOOK]


def test_a_failing_test_message_is_a_502_that_does_not_leak_the_url(world, client, monkeypatch):
    def fail(payload, webhook_url=None):
        raise ConnectionError(f"could not reach {webhook_url}")

    monkeypatch.setattr(slack, "post_to_slack", fail)
    _, h = _signed_in(world, client)
    client.put("/api/slack", json={"webhook_url": HOOK}, headers=h)
    res = client.post("/api/slack/test", headers=h)
    assert res.status_code == 502 and "secretsecret" not in res.get_data(as_text=True)


def test_each_tenant_sees_and_tests_only_its_own(world, client, posts):
    _, ha = _signed_in(world, client)
    client.put("/api/slack", json={"webhook_url": HOOK}, headers=ha)
    client.post("/api/auth/logout", json={}, headers=ha)
    _, hb = _signed_in(world, client)
    assert client.get("/api/slack", headers=hb).get_json()["configured"] is False
    assert client.post("/api/slack/test", headers=hb).status_code == 409
    assert posts == []


def test_it_needs_a_session(client):
    assert client.get("/api/slack").status_code == 401
    assert client.put("/api/slack", json={"webhook_url": HOOK}).status_code == 401
