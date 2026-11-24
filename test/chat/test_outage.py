"""When every model fails, /chat answers 200 with the busy text, saves no AI message, and alerts Slack once an hour."""

import uuid

import groq
import httpx
import pytest
from langchain_core.runnables import RunnableLambda

from chat import engine, outage
from chat.history import read_history
from core import db_pool, throttle
from summary import slack
from whatsapp import service as wa_service

REQUEST = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")


def _rate_limit() -> groq.RateLimitError:
    return groq.RateLimitError("rate limited", response=httpx.Response(429, request=REQUEST), body=None)


def _server_error() -> groq.InternalServerError:
    return groq.InternalServerError("boom", response=httpx.Response(503, request=REQUEST), body=None)


@pytest.fixture
def failing_model(monkeypatch):
    """A chat model that always raises what the test sets in box['exc']."""
    box = {"exc": _rate_limit()}

    def fail(_):
        raise box["exc"]

    monkeypatch.setattr(engine, "get_chat_model", lambda: RunnableLambda(fail))
    monkeypatch.setattr(engine, "process_conversation", lambda *a: None)
    monkeypatch.setattr(engine, "get_prompt", lambda *a: "system prompt")
    return box


@pytest.fixture
def alerts(monkeypatch):
    """Slack calls recorded instead of sent, and a clean throttle row for the alert."""
    sent = []
    monkeypatch.setattr(slack.config, "SLACK_WEBHOOK_URL", "https://hooks.invalid/x")
    monkeypatch.setattr(slack, "post_to_slack", lambda payload, webhook_url=None: sent.append(payload))
    _clear_throttle()
    yield sent
    _clear_throttle()


def _clear_throttle():
    throttle._memory.clear()
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM alert_throttle WHERE key = %s", (outage.ALERT_KEY,))


@pytest.fixture
def session_id():
    sid = str(uuid.uuid4())
    yield sid
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM chat_table WHERE session_id = %s", (sid,))


def _post(client, session_id):
    return client.post(
        "/chat?origin=https%3A%2F%2Fexample.com",
        json={"input": "What do you sell?", "session_id": session_id, "request_type": "sales"},
    )


def test_a_rate_limit_gives_200_degraded_and_no_ai_message(client, failing_model, alerts, session_id):
    res = _post(client, session_id)
    assert res.status_code == 200
    assert res.get_json() == {"success": True, "response": outage.BUSY_REPLY, "degraded": True}
    # The question is kept; the busy text is not stored as if the model had said it.
    assert read_history(session_id) == [{"type": "human", "content": "What do you sell?"}]


@pytest.mark.parametrize("exc", [_server_error(), groq.APITimeoutError(request=REQUEST)])
def test_5xx_and_timeouts_degrade_too(client, failing_model, alerts, session_id, exc):
    failing_model["exc"] = exc
    res = _post(client, session_id)
    assert res.status_code == 200 and res.get_json()["degraded"] is True


def test_a_bug_that_is_not_an_outage_is_still_a_500(client, failing_model, alerts, session_id):
    failing_model["exc"] = RuntimeError("our bug")
    assert _post(client, session_id).status_code == 500
    assert alerts == []


def test_the_slack_alert_is_sent_once_an_hour(client, failing_model, alerts):
    for _ in range(3):
        assert _post(client, str(uuid.uuid4())).get_json()["degraded"] is True
    assert len(alerts) == 1
    assert "Chat is degraded" in alerts[0]["text"] and "RateLimitError" in alerts[0]["text"]


def test_the_throttle_lets_one_alert_through_per_interval(alerts):
    assert throttle.claim("t-key", 3600) is True
    assert throttle.claim("t-key", 3600) is False
    assert throttle.claim("t-key", 0) is True  # an interval that has passed
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM alert_throttle WHERE key = 't-key'")


def test_the_throttle_falls_back_to_memory_without_a_database(monkeypatch):
    def down(*a, **k):
        raise RuntimeError("db down")

    monkeypatch.setattr(throttle, "_claim_in_db", down)
    throttle._memory.pop("mem-key", None)
    assert throttle.claim("mem-key") is True
    assert throttle.claim("mem-key") is False
    throttle._memory.pop("mem-key", None)


def test_a_failing_slack_post_does_not_break_the_reply(client, failing_model, alerts, monkeypatch, session_id):
    def broken(payload, webhook_url=None):
        raise RuntimeError("slack down")

    monkeypatch.setattr(slack, "post_to_slack", broken)
    assert _post(client, session_id).status_code == 200


def test_whatsapp_replies_with_the_busy_text(monkeypatch):
    sent = []
    monkeypatch.setattr(wa_service, "send_text", lambda pnid, token, to, body: sent.append(body) or _ok())
    monkeypatch.setattr(wa_service.tenancy, "conversation_allowed", lambda *a: True)
    monkeypatch.setattr(wa_service.repository, "ensure_chat_info", lambda *a: None)

    def unavailable(*a):
        raise outage.LLMUnavailable("429")

    monkeypatch.setattr(wa_service, "get_groq_response", unavailable)
    conn = {"phone_number_id": "1", "domain_key": "COMMON", "access_token": "t", "id": "c"}
    wa_service.handle_text(conn, "919999999999", "Ann", "hi")
    assert sent == [outage.BUSY_REPLY]


def _ok():
    from whatsapp.client import GraphResult

    return GraphResult(True, {})
