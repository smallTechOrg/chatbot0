"""Monthly conversation caps by plan: counted per calendar month (Asia/Kolkata), no LLM call over the cap."""

import re
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from conftest import sign_in

from api import chat as chat_api
from core import db_pool
from tenancy import plans, service

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def small_caps(monkeypatch):
    """Tiny caps so a test does not need hundreds of leads."""
    monkeypatch.setattr(plans, "PLAN_LIMITS", {"free": 2, "basic": 3, "pro": None})


def test_the_caps_match_the_pricing_page():
    text = Path(__file__).resolve().parents[2].joinpath("frontend/src/content/plans.ts").read_text()
    found = re.findall(r'key: "(\w+)".*?\["([\d,]+|Unlimited) conversations', text, flags=re.S)
    expected = {key: None if n == "Unlimited" else int(n.replace(",", "")) for key, n in found}
    assert expected == plans.PLAN_LIMITS


def test_the_month_starts_at_midnight_on_the_first_in_kolkata():
    # 20:00 UTC on 31 Oct is already 1:30 am on 1 Nov in India.
    now = datetime(2026, 10, 31, 20, 0, tzinfo=ZoneInfo("UTC"))
    assert plans.month_start(now) == datetime(2026, 11, 1, 0, 0, tzinfo=IST)
    assert plans.month_start(datetime(2026, 11, 15, 12, 0, tzinfo=IST)) == datetime(2026, 11, 1, tzinfo=IST)


def test_an_enabled_free_tenant_is_blocked_over_its_cap(world, small_caps):
    t = world.tenant("Free", plan="free")
    for _ in range(2):
        world.lead(t["key"])
    assert service.block_reply(t["key"], "new-session") == plans.PLAN_LIMIT_REPLY
    assert not service.conversation_allowed(t["key"], "new-session")


def test_under_the_cap_is_allowed(world, small_caps):
    t = world.tenant("Free", plan="free")
    world.lead(t["key"])
    assert service.block_reply(t["key"], "new-session") is None


def test_a_started_conversation_continues_over_the_cap(world, small_caps):
    t = world.tenant("Free", plan="free")
    started = world.lead(t["key"])
    world.lead(t["key"])
    assert service.block_reply(t["key"], started) is None


def test_the_plan_sets_the_cap(world, small_caps):
    basic = world.tenant("Basic", plan="basic")
    for _ in range(2):
        world.lead(basic["key"])
    assert service.block_reply(basic["key"], "new") is None  # 2 of 3
    world.lead(basic["key"])
    assert service.block_reply(basic["key"], "new") == plans.PLAN_LIMIT_REPLY


def test_the_unlimited_plan_has_no_cap(world, small_caps):
    t = world.tenant("Pro", plan="pro")
    for _ in range(5):
        world.lead(t["key"])
    assert service.block_reply(t["key"], "new") is None


def test_only_this_months_sessions_count(world, small_caps):
    t = world.tenant("Free", plan="free")
    last_month = plans.month_start() - timedelta(days=1)
    for _ in range(3):
        world.lead(t["key"], created_at=last_month)
    assert service.block_reply(t["key"], "new") is None
    world.lead(t["key"])
    world.lead(t["key"], created_at=plans.month_start() + timedelta(minutes=1))
    assert service.block_reply(t["key"], "new") == plans.PLAN_LIMIT_REPLY


def test_the_count_spans_all_of_the_tenants_domains_and_only_its_own(world, small_caps):
    a, b = world.tenant("A"), world.tenant("B")
    world.domain(a["id"], a["key"] + "_2")
    world.lead(a["key"])
    world.lead(a["key"] + "_2")
    world.lead(b["key"])
    assert service.block_reply(a["key"], "new") == plans.PLAN_LIMIT_REPLY
    assert service.block_reply(b["key"], "new") is None


def test_a_tenant_not_enabled_keeps_the_trial_cap_not_the_plan_cap(world, small_caps):
    t = world.tenant("Trial", enabled=False, limit=1, plan="pro")
    world.lead(t["key"])
    assert service.block_reply(t["key"], "new") == service.TRIAL_LIMIT_REPLY


def test_the_chat_api_answers_the_fixed_reply_without_an_llm_call(world, client, small_caps, monkeypatch):
    t = world.tenant("Free", plan="free")
    for _ in range(2):
        world.lead(t["key"])
    calls = []
    monkeypatch.setattr(chat_api, "get_groq_response", lambda *a: calls.append(a) or "llm")
    monkeypatch.setattr(chat_api, "chat_api_validate", _valid_for(t["key"]))
    res = client.post("/chat", json={"input": "hi", "session_id": "0b8a6c0e-7a3c-4a5e-9d8f-444444444444"})
    assert res.status_code == 200
    assert res.get_json()["response"] == plans.PLAN_LIMIT_REPLY
    assert calls == []


def _valid_for(key):
    from api.models import ValidationResponse

    return lambda request: ValidationResponse(True, "", {"request_type": "sales", "domain": key})


def _tenant_row(tenant_id):
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT plan FROM tenants WHERE id = %s", (tenant_id,))
        return cur.fetchone()[0]


def test_the_smalltech_tenant_is_on_the_unlimited_plan():
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT plan FROM tenants WHERE name = 'smallTech'")
        assert cur.fetchone()[0] == plans.UNLIMITED_PLAN


def test_new_tenants_start_on_free(world):
    with db_pool.get_connection() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO tenants (name) VALUES ('plan-default-test') RETURNING id")
        tid = cur.fetchone()[0]
    world.tenants.append(tid)
    assert _tenant_row(tid) == "free"


def test_admins_set_the_plan(world, client):
    admin_tenant = world.tenant("Admins")
    world.user(admin_tenant["id"], f"admin{admin_tenant['id']}@x.test", is_admin=True)
    csrf = sign_in(client, f"admin{admin_tenant['id']}@x.test")
    other = world.tenant("Customer")
    res = client.patch(f"/api/admin/tenants/{other['id']}", json={"plan": "basic"}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 200 and res.get_json()["tenant"]["plan"] == "basic"
    assert _tenant_row(other["id"]) == "basic"
    bad = client.patch(f"/api/admin/tenants/{other['id']}", json={"plan": "gold"}, headers={"X-CSRF-Token": csrf})
    assert bad.status_code == 400
    listing = client.get("/api/admin/tenants").get_json()["tenants"]
    mine = next(t for t in listing if t["id"] == other["id"])
    assert mine["plan"] == "basic" and mine["monthly_limit"] == 1000 and "month_conversations" in mine


def test_a_customer_cannot_change_its_own_plan(world, client):
    t = world.tenant("Customer")
    world.user(t["id"], f"c{t['id']}@x.test")
    csrf = sign_in(client, f"c{t['id']}@x.test")
    res = client.patch(f"/api/admin/tenants/{t['id']}", json={"plan": "pro"}, headers={"X-CSRF-Token": csrf})
    assert res.status_code == 403 and _tenant_row(t["id"]) == "free"


def test_me_shows_usage_against_the_cap(world, client, small_caps):
    t = world.tenant("Customer", plan="free")
    world.user(t["id"], f"c{t['id']}@x.test")
    world.lead(t["key"])
    sign_in(client, f"c{t['id']}@x.test")
    tenant = client.get("/api/auth/me").get_json()["tenant"]
    assert (tenant["plan"], tenant["plan_name"]) == ("free", "Free")
    assert (tenant["monthly_limit"], tenant["monthly_conversations_used"]) == (2, 1)
