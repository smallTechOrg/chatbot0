"""Who may connect and manage WhatsApp numbers, and how: the rules behind /api/whatsapp/connections.

A tenant user reaches the connections on their own tenant's domains and, when the tenant is enabled, can add and change
them. An admin reaches all. Credentials are never returned.
"""

from __future__ import annotations

from typing import Any

from core.errors import ServiceError
from tenancy import repository as tenants
from whatsapp import repository
from whatsapp.client import check_number, send_text
from whatsapp.input import PHONE_NUMBER_ID, RECIPIENT, SEND_HINTS, clean, clean_id

DEFAULT_TEST_BODY = "Test message from chatbot0. Reply to chat with the bot."


class WhatsAppError(ServiceError):
    """A WhatsApp request the API answers with `status` and a message that is safe to show."""


def _owned_keys(user: dict[str, Any]) -> set[str] | None:
    """The domain keys the user may use; None means all (admin)."""
    return None if user["is_admin"] else set(tenants.domain_keys(user["tenant_id"]))


def _require_active(user: dict[str, Any]) -> None:
    tenant = tenants.find_tenant(user["tenant_id"])
    if not user["is_admin"] and not (tenant and tenant["enabled"]):
        raise WhatsAppError("Your account is not active yet, so WhatsApp is read-only.", 403)


def list_connections(user: dict[str, Any]) -> list[dict[str, Any]]:
    keys = _owned_keys(user)
    return [c for c in repository.list_connections() if keys is None or c["domain_key"] in keys]


def get_connection(user: dict[str, Any], connection_id: str) -> dict[str, Any]:
    connection = repository.get_connection(connection_id)
    if connection is None:
        raise WhatsAppError("No such connection.", 404)
    keys = _owned_keys(user)
    if keys is not None and connection["domain_key"] not in keys:
        raise WhatsAppError("This connection belongs to another account.", 403)
    return connection


def domain_keys(user: dict[str, Any]) -> list[str]:
    return tenants.domain_keys(None if user["is_admin"] else user["tenant_id"])


def _check(connection_id: str, phone_number_id: str, token: str) -> dict[str, Any]:
    """Ask the Graph API whether the token works for this number and record the answer."""
    result = check_number(phone_number_id, token)
    if result.ok:
        data = result.data or {}
        repository.mark_checked(connection_id, data.get("display_phone_number"), data.get("verified_name"))
        return {
            "ok": True,
            "display_number": data.get("display_phone_number"),
            "verified_name": data.get("verified_name"),
        }
    repository.mark_error(connection_id, result.error or "check failed", needs_attention=True)
    return {"ok": False, "error": result.error}


def create(user: dict[str, Any], data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Connect a number. Returns (connection, token check result)."""
    _require_active(user)
    raw_id = data.get("phone_number_id") if isinstance(data.get("phone_number_id"), str) else ""
    fields = {
        k: clean(data[k]) if isinstance(data.get(k), str) else "" for k in ("domain_key", "access_token", "app_secret")
    }
    fields["phone_number_id"] = clean_id(raw_id)
    if not PHONE_NUMBER_ID.match(fields["phone_number_id"]):
        raise WhatsAppError(
            "Phone number ID must be the long numeric ID from WhatsApp > API Setup (not the phone number).", 400
        )
    if not all(fields.values()):
        raise WhatsAppError("Phone number ID, domain, access token and app secret are all required.", 400)
    keys = _owned_keys(user)
    if keys is not None and fields["domain_key"] not in keys:
        raise WhatsAppError("That website does not belong to your account.", 403)
    try:
        created = repository.create_connection(**fields)
    except repository.DomainNotFound:
        raise WhatsAppError(f"No domain with key {fields['domain_key']}.", 404) from None
    except repository.NumberAlreadyConnected:
        raise WhatsAppError("That number is already connected.", 409) from None
    return created, _check(created["id"], fields["phone_number_id"], fields["access_token"])


def update_credentials(user: dict[str, Any], connection_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    """Replace the token, app secret and/or domain. Returns the token check result when a token was given."""
    _require_active(user)
    get_connection(user, connection_id)
    token = clean(data["access_token"]) if isinstance(data.get("access_token"), str) else ""
    secret = clean(data["app_secret"]) if isinstance(data.get("app_secret"), str) else ""
    domain_key = clean(data["domain_key"]) if isinstance(data.get("domain_key"), str) else ""
    if not (token or secret or domain_key):
        raise WhatsAppError("Nothing to change.", 400)
    keys = _owned_keys(user)
    if domain_key and keys is not None and domain_key not in keys:
        raise WhatsAppError("That website does not belong to your account.", 403)
    try:
        repository.update_credentials(connection_id, token or None, secret or None, domain_key or None)
    except repository.DomainNotFound:
        raise WhatsAppError(f"No domain with key {domain_key}.", 404) from None
    if not token:
        return None
    full = repository.get_connection_with_credentials(connection_id)
    return _check(connection_id, full["phone_number_id"], full["access_token"])


def check(user: dict[str, Any], connection_id: str) -> dict[str, Any]:
    _require_active(user)
    get_connection(user, connection_id)
    full = repository.get_connection_with_credentials(connection_id)
    return _check(connection_id, full["phone_number_id"], full["access_token"])


def send_test(user: dict[str, Any], connection_id: str, data: dict[str, Any]) -> dict[str, Any]:
    _require_active(user)
    get_connection(user, connection_id)
    full = repository.get_connection_with_credentials(connection_id)
    to = str(data.get("to") or "").replace(" ", "").replace("-", "")
    body = (data.get("body") or "").strip() if isinstance(data.get("body"), str) else ""
    if not RECIPIENT.match(to):
        raise WhatsAppError("Enter the recipient with country code, digits only, e.g. 919876543210.", 400)
    result = send_text(full["phone_number_id"], full["access_token"], to.lstrip("+"), body or DEFAULT_TEST_BODY)
    if result.ok:
        return {"ok": True, "to": f"+{to.lstrip('+')}"}
    if result.token_problem:
        repository.mark_error(connection_id, result.error or "send failed", needs_attention=True)
    return {"ok": False, "error": result.error, "hint": SEND_HINTS.get(result.code, "")}
