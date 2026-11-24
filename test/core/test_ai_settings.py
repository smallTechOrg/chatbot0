"""The platform AI provider: DB setting over env, 60 s cache, key never exposed, backup on failure, admin-only."""

import uuid

import groq
import httpx
import openai
import pytest
from conftest import sign_in
from langchain_core.runnables import RunnableLambda, RunnableWithFallbacks
from langchain_openai import ChatOpenAI

from core import ai_settings, config, db_pool, llm
from tenancy import ai_provider

SECRET = "sk-test-SUPER-SECRET-key-123"
GOOD = {
    "base_url": "https://llm.example.test/v1",
    "api_key": SECRET,
    "model": "big-model",
    "backup_model": "small-model",
    "timeout_seconds": 30,
}


@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "unit-test-secret-key")
    _wipe()
    yield
    _wipe()


def _wipe():
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM ai_provider_settings")
    ai_settings.invalidate()


def _admin(app, world):
    t = world.tenant("Admins")
    email = f"a{uuid.uuid4().hex[:6]}@ai.test"
    world.user(t["id"], email, is_admin=True)
    client = app.test_client()
    return client, {"X-CSRF-Token": sign_in(client, email)}


def _stored_key():
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT api_key_enc FROM ai_provider_settings WHERE id = 1")
        return cur.fetchone()[0]


# ---------------------------------------------------------------- DB setting over env


def test_without_a_db_setting_the_groq_environment_is_used(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(config, "GROQ_MODEL_NAME", "env-model")
    monkeypatch.setattr(config, "GROQ_BACKUP_MODEL_NAME", None)
    model = llm.get_chat_model()
    assert type(model).__name__ == "ChatGroq" and model.model_name == "env-model"


def test_the_db_setting_overrides_the_environment(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "dummy")
    monkeypatch.setattr(config, "GROQ_MODEL_NAME", "env-model")
    ai_provider.save({**GOOD, "backup_model": None})
    model = llm.get_chat_model()
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "big-model"
    assert str(model.openai_api_base) == "https://llm.example.test/v1"
    assert model.openai_api_key.get_secret_value() == SECRET
    assert model.request_timeout == 30


def test_a_backup_model_becomes_a_fallback_on_the_custom_endpoint():
    ai_provider.save(GOOD)
    model = llm.get_chat_model()
    assert isinstance(model, RunnableWithFallbacks)
    assert model.runnable.model_name == "big-model"
    assert [m.model_name for m in model.fallbacks] == ["small-model"]


def test_a_failing_primary_uses_the_backup(monkeypatch):
    ai_provider.save(GOOD)

    def build(settings, name):
        if name == "big-model":
            return RunnableLambda(lambda _: (_ for _ in ()).throw(RuntimeError("primary down")))
        return RunnableLambda(lambda _: f"answered by {name}")

    monkeypatch.setattr(llm, "_openai", build)
    assert llm.get_chat_model().invoke("hi") == "answered by small-model"


def test_every_llm_user_gets_the_same_factory():
    import chat.engine
    import chat.lead_capture
    import summary.periodic

    assert chat.engine.get_chat_model is llm.get_chat_model
    assert chat.lead_capture.get_chat_model is llm.get_chat_model
    assert summary.periodic.get_chat_model is llm.get_chat_model


# ---------------------------------------------------------------- the 60 second cache


def test_the_setting_is_cached_and_expires(monkeypatch):
    ai_provider.save(GOOD)
    reads = []
    real = ai_settings._read_row
    monkeypatch.setattr(ai_settings, "_read_row", lambda: reads.append(1) or real())
    clock = [1000.0]
    monkeypatch.setattr(ai_settings.time, "monotonic", lambda: clock[0])
    ai_settings.invalidate()

    assert ai_settings.get_settings()["model"] == "big-model"
    clock[0] += ai_settings.CACHE_SECONDS - 1
    ai_settings.get_settings()
    assert len(reads) == 1  # still cached

    # Another instance changes the row; this one does not see it until the cache expires.
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("UPDATE ai_provider_settings SET model = 'changed-model'")
    assert ai_settings.get_settings()["model"] == "big-model"
    clock[0] += 2
    assert ai_settings.get_settings()["model"] == "changed-model"
    assert len(reads) == 2


def test_saving_on_this_instance_takes_effect_at_once():
    ai_provider.save(GOOD)
    assert ai_settings.get_settings()["model"] == "big-model"
    ai_provider.save({**GOOD, "model": "newer-model"})
    assert ai_settings.get_settings()["model"] == "newer-model"


def test_a_database_error_keeps_the_last_value(monkeypatch):
    ai_provider.save(GOOD)
    assert ai_settings.get_settings()["model"] == "big-model"
    clock = [5000.0]
    monkeypatch.setattr(ai_settings.time, "monotonic", lambda: clock[0])
    ai_settings._cache["at"] = 0.0  # expired

    def down():
        raise RuntimeError("db down")

    monkeypatch.setattr(ai_settings, "_read_row", down)
    assert ai_settings.get_settings()["model"] == "big-model"


def test_an_undecryptable_key_falls_back_to_the_environment(monkeypatch):
    ai_provider.save(GOOD)
    ai_settings.invalidate()
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "a-different-key")
    assert ai_settings.get_settings() is None


# ---------------------------------------------------------------- the admin API


def test_the_key_is_encrypted_at_rest_and_never_in_any_response(app, world):
    client, h = _admin(app, world)
    res = client.put("/api/admin/ai-provider", json=GOOD, headers=h)
    assert res.status_code == 200
    stored = _stored_key()
    assert stored and SECRET not in stored
    for response in (res, client.get("/api/admin/ai-provider")):
        text = response.get_data(as_text=True)
        assert SECRET not in text and "api_key" not in text
    body = client.get("/api/admin/ai-provider").get_json()
    assert body["source"] == "database" and body["key_set"] is True and body["model"] == "big-model"
    assert body["backup_model"] == "small-model" and body["timeout_seconds"] == 30


def test_saving_without_a_key_keeps_the_stored_one(app, world):
    client, h = _admin(app, world)
    client.put("/api/admin/ai-provider", json=GOOD, headers=h)
    before = _stored_key()
    res = client.put("/api/admin/ai-provider", json={**GOOD, "api_key": None, "model": "other"}, headers=h)
    assert res.status_code == 200 and _stored_key() == before
    assert ai_settings.get_settings()["api_key"] == SECRET and ai_settings.get_settings()["model"] == "other"


def test_with_no_setting_the_page_reports_the_environment(app, world, monkeypatch):
    monkeypatch.setattr(config, "GROQ_MODEL_NAME", "env-model")
    client, _ = _admin(app, world)
    body = client.get("/api/admin/ai-provider").get_json()
    assert body["source"] == "environment" and body["model"] == "env-model" and body["base_url"] is None


def test_removing_the_setting_goes_back_to_the_environment(app, world):
    client, h = _admin(app, world)
    client.put("/api/admin/ai-provider", json=GOOD, headers=h)
    assert client.delete("/api/admin/ai-provider", headers=h).get_json()["source"] == "environment"
    assert ai_settings.get_settings() is None


@pytest.mark.parametrize(
    "change",
    [
        {"base_url": "http://llm.example.test/v1"},
        {"base_url": "not a url"},
        {"base_url": ""},
        {"model": ""},
        {"model": "has space"},
        {"timeout_seconds": 0},
        {"timeout_seconds": 301},
        {"timeout_seconds": "30"},
        {"api_key": 5},
    ],
)
def test_bad_input_is_a_422_and_stores_nothing(app, world, change):
    client, h = _admin(app, world)
    assert client.put("/api/admin/ai-provider", json={**GOOD, **change}, headers=h).status_code == 422
    assert ai_settings.public_view() is None


def test_http_is_allowed_for_localhost_only(app, world):
    client, h = _admin(app, world)
    ok = client.put("/api/admin/ai-provider", json={**GOOD, "base_url": "http://localhost:11434/v1"}, headers=h)
    assert ok.status_code == 200


def test_only_admins_can_see_or_change_it(app, world):
    t = world.tenant("Customer")
    world.user(t["id"], f"c{t['id']}@ai.test")
    client = app.test_client()
    h = {"X-CSRF-Token": sign_in(client, f"c{t['id']}@ai.test")}
    assert client.get("/api/admin/ai-provider").status_code == 403
    assert client.put("/api/admin/ai-provider", json=GOOD, headers=h).status_code == 403
    assert client.delete("/api/admin/ai-provider", headers=h).status_code == 403
    assert client.post("/api/admin/ai-provider/test", headers=h).status_code == 403
    assert app.test_client().get("/api/admin/ai-provider").status_code == 401
    assert ai_settings.public_view() is None


# ---------------------------------------------------------------- the connection test


def _http_error(cls, status):
    request = httpx.Request("POST", "https://llm.example.test/v1/chat/completions")
    return cls(f"leaked {SECRET}", response=httpx.Response(status, request=request), body=None)


def test_the_connection_test_reports_ok(app, world, monkeypatch):
    client, h = _admin(app, world)
    client.put("/api/admin/ai-provider", json=GOOD, headers=h)
    monkeypatch.setattr(llm, "_openai", lambda s, name: RunnableLambda(lambda _, **kw: "OK"))
    body = client.post("/api/admin/ai-provider/test", headers=h).get_json()
    assert body["ok"] is True
    assert [(r["role"], r["model"], r["ok"]) for r in body["results"]] == [
        ("primary", "big-model", True),
        ("backup", "small-model", True),
    ]


def test_a_failed_connection_test_shows_the_error_type_and_never_the_key(app, world, monkeypatch):
    client, h = _admin(app, world)
    client.put("/api/admin/ai-provider", json=GOOD, headers=h)

    def build(settings, name):
        def fail(_, **kw):
            raise _http_error(openai.AuthenticationError, 401)

        return RunnableLambda(fail)

    monkeypatch.setattr(llm, "_openai", build)
    res = client.post("/api/admin/ai-provider/test", headers=h)
    assert SECRET not in res.get_data(as_text=True)
    first = res.get_json()["results"][0]
    assert res.get_json()["ok"] is False
    assert first["ok"] is False and first["error"] == "HTTP 401 (AuthenticationError)"


# ---------------------------------------------------------------- outage detection covers both libraries


@pytest.mark.parametrize(
    "exc",
    [
        _http_error(openai.RateLimitError, 429),
        _http_error(openai.InternalServerError, 503),
        _http_error(groq.RateLimitError, 429),
        openai.APITimeoutError(request=httpx.Request("POST", "https://x.test")),
    ],
)
def test_outages_from_either_client_are_recognised(exc):
    assert llm.is_outage(exc)


def test_a_bad_key_is_not_an_outage():
    assert not llm.is_outage(_http_error(openai.AuthenticationError, 401))
    assert not llm.is_outage(RuntimeError("bug"))
