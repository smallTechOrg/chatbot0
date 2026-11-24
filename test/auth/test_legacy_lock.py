"""LOCK_LEGACY_API: the old public endpoints become admin-only; everything the widget and Meta need stays public."""

import pytest
from conftest import sign_in

from auth.legacy import LOCKED, is_locked
from core import config

LEGACY = [
    ("get", "/chat-info"),
    ("patch", "/chat-info"),
    ("patch", "/chat-info/contact"),
    ("get", "/prompts"),
    ("post", "/prompt"),
    ("get", "/domains/"),
    ("post", "/domains/"),
    ("get", "/domains/1"),
]
STAYS_PUBLIC = [("post", "/chat"), ("get", "/history"), ("get", "/health"), ("get", "/api/auth/status")]


@pytest.fixture
def people(world):
    t = world.tenant("Lock")
    world.user(t["id"], "user@lock-test.invalid")
    world.user(t["id"], "root@lock-test.invalid", is_admin=True)


def call(client, method, path, headers=None):
    return getattr(client, method)(path, json={}, headers=headers or {})


@pytest.mark.parametrize("method,path", LEGACY)
def test_the_lock_is_off_by_default(client, method, path):
    assert config.LOCK_LEGACY_API is False
    assert call(client, method, path).status_code not in (401, 403)


@pytest.mark.parametrize("method,path", LEGACY)
def test_locked_endpoints_need_a_session(client, monkeypatch, people, method, path):
    monkeypatch.setattr(config, "LOCK_LEGACY_API", True)
    assert call(client, method, path).status_code == 401


@pytest.mark.parametrize("method,path", LEGACY)
def test_locked_endpoints_refuse_ordinary_users(app, monkeypatch, people, method, path):
    monkeypatch.setattr(config, "LOCK_LEGACY_API", True)
    client = app.test_client()
    csrf = sign_in(client, "user@lock-test.invalid")
    assert call(client, method, path, {"X-CSRF-Token": csrf}).status_code == 403


@pytest.mark.parametrize("method,path", LEGACY)
def test_admins_still_reach_them(app, monkeypatch, people, method, path):
    monkeypatch.setattr(config, "LOCK_LEGACY_API", True)
    client = app.test_client()
    csrf = sign_in(client, "root@lock-test.invalid")
    assert call(client, method, path, {"X-CSRF-Token": csrf}).status_code not in (401, 403)


def test_an_admin_changing_data_needs_the_csrf_token(app, monkeypatch, people):
    monkeypatch.setattr(config, "LOCK_LEGACY_API", True)
    client = app.test_client()
    sign_in(client, "root@lock-test.invalid")
    assert client.patch("/chat-info", json={}).status_code == 403
    assert client.get("/chat-info").status_code == 200  # reads need no token


@pytest.mark.parametrize("method,path", STAYS_PUBLIC)
def test_the_widget_and_health_stay_public(client, monkeypatch, method, path):
    monkeypatch.setattr(config, "LOCK_LEGACY_API", True)
    assert call(client, method, path).status_code not in (401, 403)


def test_the_webhook_and_job_endpoints_stay_with_their_own_checks(client, monkeypatch):
    monkeypatch.setattr(config, "LOCK_LEGACY_API", True)
    assert client.get("/whatsapp/webhook/nope?hub.mode=subscribe").status_code == 403  # Meta's handshake, own check
    assert client.post("/jobs/periodic-summary").status_code in (401, 403, 503)  # OIDC, own check


def test_unknown_paths_and_the_frontend_are_not_caught(client, monkeypatch):
    monkeypatch.setattr(config, "LOCK_LEGACY_API", True)
    assert client.get("/").status_code == 200
    assert client.get("/prompts-and-more/").status_code == 404


def test_the_lock_table_matches_the_routes_that_exist(app):
    rules = {(r.rule, m) for r in app.url_map.iter_rules() for m in r.methods}
    for rule, methods in LOCKED.items():
        for method in methods:
            assert (rule, method) in rules, f"{method} {rule} is locked but no such route exists"
    assert is_locked("/prompt", "POST") and not is_locked("/prompt", "GET") and not is_locked(None, "GET")
