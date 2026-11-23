"""Admin pages: sign-in, CSRF, and the WhatsApp connection flows (Graph API stubbed)."""
import os
import re
import sys
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import admin  # noqa: E402
import config  # noqa: E402
import crypto  # noqa: E402
from app import app as flask_app  # noqa: E402
from db_pool import get_connection  # noqa: E402
from whatsapp import repository  # noqa: E402
from whatsapp.client import GraphResult  # noqa: E402

PASSWORD = "admin-pass-for-tests"


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_SECRET_KEY", "unit-test-secret-key")
    monkeypatch.setattr(config, "CHATBOT0_ADMIN_PASSWORD", PASSWORD)
    monkeypatch.setattr(flask_app, "secret_key", crypto.session_signing_key())
    monkeypatch.setattr(admin, "check_number", lambda pnid, token: GraphResult(
        True, {"display_phone_number": "+1 555 0100", "verified_name": "Test Biz"}))


@pytest.fixture
def client():
    return flask_app.test_client()


def csrf(client, path):
    html = client.get(path).get_data(as_text=True)
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def login(client):
    token = csrf(client, "/chatbot0/admin/login")
    r = client.post("/chatbot0/admin/login", data={"password": PASSWORD, "csrf": token})
    assert r.status_code == 302
    return csrf(client, "/chatbot0/admin/whatsapp")


@pytest.fixture
def cleanup():
    created = []
    yield created
    with get_connection() as conn:
        with conn.cursor() as cur:
            for pnid in created:
                cur.execute("DELETE FROM whatsapp_connections WHERE phone_number_id = %s;", (pnid,))
        conn.commit()


def test_pages_need_sign_in(client):
    r = client.get("/chatbot0/admin/whatsapp")
    assert r.status_code == 302 and "/chatbot0/admin/login" in r.headers["Location"]


def test_wrong_password_and_missing_csrf(client):
    token = csrf(client, "/chatbot0/admin/login")
    r = client.post("/chatbot0/admin/login", data={"password": "nope", "csrf": token})
    assert r.status_code == 200 and "Wrong password" in r.get_data(as_text=True)
    assert client.post("/chatbot0/admin/login", data={"password": PASSWORD}).status_code == 400


def test_disabled_without_configuration(client, monkeypatch):
    monkeypatch.setattr(config, "CHATBOT0_ADMIN_PASSWORD", "")
    assert client.get("/chatbot0/admin/login").status_code == 503


def test_connect_number_shows_webhook_and_hides_secrets(client, cleanup):
    token = login(client)
    domain = client.get("/chatbot0/admin/whatsapp").get_data(as_text=True)
    key = re.search(r'<option value="([^"]+)"', domain).group(1)
    pnid = str(uuid.uuid4().int)[:15]
    cleanup.append(pnid)
    r = client.post("/chatbot0/admin/whatsapp", data={
        "csrf": token, "phone_number_id": pnid, "domain_key": key,
        "access_token": "EAAsecret-token-value", "app_secret": "super-app-secret"})
    assert r.status_code == 302
    page = client.get(r.headers["Location"]).get_data(as_text=True)
    conn_id = r.headers["Location"].rsplit("/", 1)[1]
    assert f"/whatsapp/webhook/{conn_id}" in page
    assert repository.get_connection(conn_id)["verify_token"] in page
    assert "EAAsecret-token-value" not in page and "super-app-secret" not in page
    assert "Test Biz" in page and repository.get_connection(conn_id)["status"] == "active"


def test_phone_number_instead_of_id_is_explained(client):
    token = login(client)
    r = client.post("/chatbot0/admin/whatsapp", data={
        "csrf": token, "phone_number_id": "+1 555 0100", "domain_key": "COMMON",
        "access_token": "x", "app_secret": "y"})
    assert "numeric ID" in r.get_data(as_text=True)


def test_test_message_outside_window_shows_hint(client, cleanup, monkeypatch):
    pnid = str(uuid.uuid4().int)[:15]
    cleanup.append(pnid)
    row = repository.create_connection(pnid, "COMMON", "tok", "sec")
    monkeypatch.setattr(admin, "send_text", lambda *a: GraphResult(False, error="HTTP 400: Re-engagement message", code=131047))
    token = login(client)
    r = client.post(f"/chatbot0/admin/whatsapp/{row['id']}/test",
                    data={"csrf": token, "to": "919876543210"}, follow_redirects=True)
    assert "last 24 hours" in r.get_data(as_text=True)
