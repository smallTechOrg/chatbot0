"""
WhatsApp: per-connection webhook (handshake, signature), payload handling,
the reply path, failure handling, and markdown conversion. The LLM and the
Graph API are stubbed; connections live in the test database.
"""
import hashlib
import hmac
import json
import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import config
import crypto
from app import app as flask_app
from db_pool import get_connection
from whatsapp import repository, service
from whatsapp.client import GraphResult, signature_is_valid
from whatsapp.formatting import split_message, to_whatsapp

APP_SECRET = "test-app-secret"
TOKEN = "EAAtest-token"
WA_ID = "917000000001"
DOMAIN = "WATEST"


@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "unit-test-secret-key")


@pytest.fixture
def client():
    return flask_app.test_client()


def _sql(query, params=()):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall() if cur.description else None
        conn.commit()
        return rows


@pytest.fixture
def connection():
    """A connection on a fresh phone_number_id, mapped to a test domain."""
    pnid = str(uuid.uuid4().int)[:16]
    _sql("INSERT INTO domains (key, address) VALUES (%s, %s) ON CONFLICT (address) DO NOTHING;",
         (DOMAIN, "watest.example"))
    row = repository.create_connection(pnid, DOMAIN, TOKEN, APP_SECRET)
    yield row
    _sql("DELETE FROM whatsapp_connections WHERE id = %s;", (row["id"],))
    _sql("DELETE FROM chat_info WHERE session_id = %s;", (service.session_id_for(pnid, WA_ID),))


@pytest.fixture
def stubs(monkeypatch):
    log = {"sent": [], "llm": [], "alerts": [], "send_result": GraphResult(True, {})}
    monkeypatch.setattr(service, "get_groq_response",
                        lambda *a: log["llm"].append(a) or "## Hello\n**Welcome** to *Acme*")

    def fake_send(pnid, token, to, body):
        log["sent"].append((pnid, token, to, body))
        return log["send_result"]

    monkeypatch.setattr(service, "send_text", fake_send)
    monkeypatch.setattr(service, "notify_whatsapp_problem", lambda c, e: log["alerts"].append(e))
    return log


def payload(pnid, text="Hi there", msg_id=None, msg_type="text"):
    msg = {"from": WA_ID, "id": msg_id or f"wamid.{uuid.uuid4().hex}", "type": msg_type}
    if msg_type == "text":
        msg["text"] = {"body": text}
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {
        "metadata": {"phone_number_id": pnid},
        "contacts": [{"wa_id": WA_ID, "profile": {"name": "Asha"}}],
        "messages": [msg],
    }}]}]}


def post(client, connection, body, secret=APP_SECRET):
    raw = json.dumps(body).encode()
    sig = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return client.post(f"/whatsapp/webhook/{connection['id']}", data=raw,
                       headers={"X-Hub-Signature-256": sig, "Content-Type": "application/json"})


# -- storage ------------------------------------------------------------------

def test_credentials_are_stored_encrypted(connection):
    stored = _sql("SELECT access_token_enc, app_secret_enc FROM whatsapp_connections WHERE id = %s;",
                  (connection["id"],))[0]
    assert TOKEN not in stored[0] and APP_SECRET not in stored[1]
    assert "access_token_enc" not in connection and "access_token" not in connection
    full = repository.get_connection_with_credentials(connection["id"])
    assert (full["access_token"], full["app_secret"]) == (TOKEN, APP_SECRET)


def test_unknown_domain_is_refused():
    with pytest.raises(repository.DomainNotFound):
        repository.create_connection("123456789", "NO_SUCH_DOMAIN_KEY", TOKEN, APP_SECRET)


def test_signature_check():
    raw = b'{"a":1}'
    good = "sha256=" + hmac.new(b"s", raw, hashlib.sha256).hexdigest()
    assert signature_is_valid(raw, good, "s")
    assert not signature_is_valid(raw, good, "other")
    assert not signature_is_valid(raw, None, "s") and not signature_is_valid(raw, good, "")


# -- handshake and signature on the route -------------------------------------

def test_handshake_echoes_challenge(client, connection):
    r = client.get(f"/whatsapp/webhook/{connection['id']}", query_string={
        "hub.mode": "subscribe", "hub.verify_token": connection["verify_token"], "hub.challenge": "8812"})
    assert (r.status_code, r.get_data(as_text=True)) == (200, "8812")


def test_handshake_rejects_wrong_token_and_unknown_connection(client, connection):
    q = {"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "1"}
    assert client.get(f"/whatsapp/webhook/{connection['id']}", query_string=q).status_code == 403
    q["hub.verify_token"] = connection["verify_token"]
    assert client.get(f"/whatsapp/webhook/{uuid.uuid4()}", query_string=q).status_code == 403


def test_wrongly_signed_post_is_refused(client, connection, stubs):
    r = post(client, connection, payload(connection["phone_number_id"]), secret="not-the-secret")
    assert r.status_code == 403 and stubs["sent"] == []


def test_post_is_refused_without_secret_key(client, connection, stubs, monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "")
    assert post(client, connection, payload(connection["phone_number_id"])).status_code == 503


# -- the reply path -----------------------------------------------------------

def test_text_message_gets_a_formatted_reply_and_a_whatsapp_lead(client, connection, stubs):
    pnid = connection["phone_number_id"]
    assert post(client, connection, payload(pnid, "What do you sell?")).status_code == 200

    text, session_id, request_type, domain = stubs["llm"][0]
    assert (text, request_type, domain) == ("What do you sell?", "sales", DOMAIN)
    assert session_id == service.session_id_for(pnid, WA_ID)
    assert stubs["sent"] == [(pnid, TOKEN, WA_ID, "*Hello*\n*Welcome* to _Acme_")]

    lead = _sql("SELECT channel, mobile, contact_name, domain FROM chat_info WHERE session_id = %s;", (session_id,))
    assert lead == [("whatsapp", "+" + WA_ID, "Asha", DOMAIN)]
    status = repository.get_connection(connection["id"])
    assert status["status"] == "active" and status["last_message_at"] is not None


def test_redelivered_message_is_answered_once(client, connection, stubs):
    body = payload(connection["phone_number_id"], msg_id=f"wamid.dup.{uuid.uuid4().hex}")
    post(client, connection, body)
    post(client, connection, body)
    assert len(stubs["sent"]) == 1


def test_media_gets_the_text_only_notice(client, connection, stubs):
    post(client, connection, payload(connection["phone_number_id"], msg_type="audio"))
    assert [s[3] for s in stubs["sent"]] == [service.TEXT_ONLY_REPLY] and stubs["llm"] == []


def test_reactions_and_read_receipts_are_ignored(client, connection, stubs):
    pnid = connection["phone_number_id"]
    post(client, connection, payload(pnid, msg_type="reaction"))
    receipt = {"object": "whatsapp_business_account", "entry": [{"changes": [{"field": "messages", "value": {
        "metadata": {"phone_number_id": pnid}, "statuses": [{"id": "x", "status": "read"}]}}]}]}
    assert post(client, connection, receipt).status_code == 200
    assert stubs["sent"] == [] and stubs["llm"] == []


def test_llm_failure_sends_the_apology(client, connection, stubs, monkeypatch):
    def boom(*a):
        raise RuntimeError("llm down")

    monkeypatch.setattr(service, "get_groq_response", boom)
    post(client, connection, payload(connection["phone_number_id"]))
    assert [s[3] for s in stubs["sent"]] == [service.FALLBACK_REPLY]


def test_rejected_send_flags_the_connection_and_alerts_once(client, connection, stubs):
    stubs["send_result"] = GraphResult(False, error="HTTP 401: Error validating access token", code=190)
    pnid = connection["phone_number_id"]
    post(client, connection, payload(pnid))
    post(client, connection, payload(pnid))
    row = repository.get_connection(connection["id"])
    assert row["status"] == "needs_attention" and "401" in row["last_error"]
    assert len(stubs["alerts"]) == 1


def test_other_numbers_on_the_same_payload_are_ignored(client, connection, stubs):
    post(client, connection, payload("999999999999"))
    assert stubs["sent"] == [] and stubs["llm"] == []


def test_session_ids_differ_per_number_and_sender():
    a = service.session_id_for("1", "100")
    assert a == service.session_id_for("1", "100")
    assert a != service.session_id_for("2", "100") and a != service.session_id_for("1", "101")
    uuid.UUID(a)


def test_changed_secret_key_makes_tokens_unreadable(connection, monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "a-different-key")
    with pytest.raises(crypto.InvalidToken):
        repository.get_connection_with_credentials(connection["id"])


# -- formatting ---------------------------------------------------------------

@pytest.mark.parametrize("md, expected", [
    ("**bold**", "*bold*"),
    ("*italic*", "_italic_"),
    ("**bold** and *italic*", "*bold* and _italic_"),
    ("## Heading\ntext", "*Heading*\ntext"),
    ("* one\n* two", "- one\n- two"),
    ("- one\n- two", "- one\n- two"),
    ("[Acme](https://acme.com)", "Acme (https://acme.com)"),
    ("2 * 3 * 4", "2 * 3 * 4"),
    ("```\n**keep**\n```", "```\n**keep**\n```"),
    ("a\n\n\n\nb", "a\n\nb"),
    ("---\ntext", "text"),
])
def test_to_whatsapp(md, expected):
    assert to_whatsapp(md) == expected


def test_split_message_respects_limit():
    text = ("word " * 50 + "\n\n") * 5
    parts = split_message(text, limit=300)
    assert all(len(p) <= 300 for p in parts) and len(parts) > 1
    assert split_message("short") == ["short"] and split_message("  ") == []
