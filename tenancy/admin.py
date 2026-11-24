"""What a chatbot0 admin does to tenants: enable them, set the trial limit, invite and reset users, move domains."""

from __future__ import annotations

from typing import Any

from auth import repository as users
from auth import service as auth
from core.errors import ServiceError
from tenancy import plans, repository

MAX_LIMIT = 100000


class AdminError(ServiceError):
    """An admin request the API answers with `status` and a message that is safe to show."""


def list_tenants() -> list[dict[str, Any]]:
    tenants = repository.list_tenants_with_usage(plans.month_start())
    return [
        {
            **t,
            "monthly_limit": plans.monthly_limit(t["plan"]),
            "domain_count": len(t["domains"]),
            "site_count": sum(1 for d in t["domains"] if not d["is_www_alias"]),
        }
        for t in tenants
    ]


def update_tenant(tenant_id: int, data: dict[str, Any]) -> dict[str, Any]:
    name, enabled, limit = data.get("name"), data.get("enabled"), data.get("trial_conversation_limit")
    plan = data.get("plan")
    if name is None and enabled is None and limit is None and plan is None:
        raise AdminError("Send name, enabled, plan or trial_conversation_limit.", 400)
    if plan is not None and (not isinstance(plan, str) or plan not in plans.PLAN_LIMITS):
        raise AdminError(f"plan must be one of: {', '.join(plans.PLAN_LIMITS)}.", 400)
    if name is not None and (not isinstance(name, str) or not name.strip() or len(name) > 200):
        raise AdminError("Name must be text of 1 to 200 characters.", 400)
    if enabled is not None and not isinstance(enabled, bool):
        raise AdminError("enabled must be true or false.", 400)
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= MAX_LIMIT):
        raise AdminError(f"trial_conversation_limit must be a whole number from 0 to {MAX_LIMIT}.", 400)
    tenant = repository.update_tenant(tenant_id, name.strip() if name else None, enabled, limit, plan)
    if tenant is None:
        raise AdminError("No such tenant.", 404)
    return tenant


def add_user(tenant_id: int, email: Any) -> tuple[dict[str, Any], str]:
    """A user without a password in the tenant, and the single-use invite token for them."""
    address = auth.normalize_email(email)
    if repository.find_tenant(tenant_id) is None:
        raise AdminError("No such tenant.", 404)
    user = users.create_user(tenant_id, address, None)
    if user is None:
        raise AdminError("A user with this email already exists.", 409)
    return user, auth.issue_token(user["id"], "invite")


def reset_link_token(user_id: int) -> tuple[dict[str, Any], str]:
    """The user and a single-use reset token (an invite token when they never set a password)."""
    user = users.find_user(user_id)
    if user is None:
        raise AdminError("No such user.", 404)
    return user, auth.issue_token(user_id, "invite" if user["password_hash"] is None else "reset")


def move_domain(key: str, tenant_id: Any) -> None:
    if isinstance(tenant_id, bool) or not isinstance(tenant_id, int):
        raise AdminError("tenant_id must be a number.", 400)
    if repository.find_tenant(tenant_id) is None:
        raise AdminError("No such tenant.", 404)
    if repository.move_domain(key, tenant_id) == 0:
        raise AdminError("No such website.", 404)
