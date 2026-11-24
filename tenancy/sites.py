"""Sign-up, a tenant's websites and their prompts: the rules behind /api/signup and /api/domains."""

from __future__ import annotations

import logging
import re
from typing import Any

from werkzeug.security import generate_password_hash

from auth import repository as users
from auth import service as auth
from auth.service import AuthError
from chat.prompt_chain import describe
from chat.prompt_store import upsert_prompt
from chat.prompts import resolve_prompt
from domains import DomainAlreadyExistsError, DomainRepository, DomainService, InvalidWebsiteURLError
from summary.slack import notify_signup
from tenancy import repository

logger = logging.getLogger(__name__)

MAX_SITES = 10
ROOT_DOMAIN_ID = 1  # COMMON: every new site inherits its prompts from it
PROMPT_TYPES = ("company", "base-prompt", "intro-message")
AGENT = "sales"
MAX_PROMPT = 20000
_PHONE = re.compile(r"^\+?[0-9 ()-]{6,20}$")


class SiteError(AuthError):
    """A request the API answers with `status` and a safe message (same shape as AuthError)."""


def _domain_service() -> DomainService:
    return DomainService(DomainRepository())


def _website(raw: Any) -> str:
    if not isinstance(raw, str) or not raw.strip() or len(raw) > 500:
        raise SiteError("Enter your website address.", 422)
    try:
        return DomainService.extract_address(raw)
    except InvalidWebsiteURLError:
        raise SiteError("Please check your website address.", 422) from None


def _optional_text(raw: Any, limit: int, label: str) -> str | None:
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str) or len(raw) > limit:
        raise SiteError(f"{label} is too long or not text.", 400)
    return raw.strip() or None


def sign_up(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create a disabled tenant, its first user and its website (with the company prompt when given).

    Returns (user, domain). 409 when the email or the website is already registered.
    """
    name = _optional_text(data.get("name"), 200, "Name")
    if not name:
        raise SiteError("Enter your name.", 400)
    email = auth.normalize_email(data.get("email"))
    password = auth.validate_password(data.get("password"))
    phone = _optional_text(data.get("phone"), 20, "Phone")
    if phone and not _PHONE.match(phone):
        raise SiteError("Please check your phone number.", 422)
    description = _optional_text(data.get("description"), MAX_PROMPT, "The business description")
    address = _website(data.get("website"))

    if DomainRepository().find_by_address(address) is not None:
        raise SiteError("This website is already signed up. Write to us at contact@smalltech.in and we'll help.", 409)
    created = repository.create_tenant_with_user(address, email, generate_password_hash(password))
    if created is None:
        raise SiteError("An account with this email already exists. Sign in instead.", 409)

    try:
        domain = _domain_service().add_domain(
            website_url=address,
            parent_id=ROOT_DOMAIN_ID,
            contact={"contact_name": name, "email": email, "mobile": phone},
            tenant_id=created["tenant_id"],
        )
    except DomainAlreadyExistsError:  # lost a race with another sign-up for the same site
        repository.delete_new_tenant(created["tenant_id"])
        raise SiteError(
            "This website is already signed up. Write to us at contact@smalltech.in and we'll help.", 409
        ) from None
    except Exception:
        repository.delete_new_tenant(created["tenant_id"])
        raise
    if description:
        upsert_prompt(domain["key"], AGENT, "company", description)
    notify_signup(domain["address"], {"contact_name": name, "email": email, "mobile": phone})
    user = users.find_user(created["id"])
    return user, domain


def list_sites(user: dict[str, Any]) -> list[dict[str, Any]]:
    return repository.list_sites(user["tenant_id"])


def add_site(user: dict[str, Any], website: Any) -> dict[str, Any]:
    """Add a website to the user's tenant: enabled tenants only, at most MAX_SITES."""
    tenant = repository.find_tenant(user["tenant_id"])
    if not tenant or not tenant["enabled"]:
        raise SiteError("Your account is not active yet, so websites cannot be added.", 403)
    address = _website(website)
    if len(repository.list_sites(tenant["id"])) >= MAX_SITES:
        raise SiteError(f"An account can have at most {MAX_SITES} websites.", 409)
    try:
        return _domain_service().add_domain(
            website_url=address, parent_id=ROOT_DOMAIN_ID, contact={}, tenant_id=tenant["id"]
        )
    except DomainAlreadyExistsError:
        raise SiteError("This website is already registered.", 409) from None


# -- prompts -----------------------------------------------------------------------------------------------------


def _owned_key(user: dict[str, Any], key: str) -> None:
    owner = repository.domain_key_tenant(key)
    if not repository.domain_key_exists(key):
        raise SiteError("No such website.", 404)
    if not user["is_admin"] and owner != user["tenant_id"]:
        raise SiteError("This website belongs to another account.", 403)


def get_prompts(user: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    """Each prompt as {text, own}: own=False means the text is inherited from an ancestor (the whole chain)."""
    _owned_key(user, key)
    result: dict[str, dict[str, Any]] = {}
    for kind in PROMPT_TYPES:
        text, source = resolve_prompt(key, AGENT, kind)
        result[kind] = {"text": text or "", "own": source == key}
    return result


def prompt_chain(user: dict[str, Any], key: str) -> dict[str, Any]:
    """The parent chain of a website and where each prompt in effect comes from (own users: their websites only)."""
    _owned_key(user, key)
    return describe(key)


def set_prompts(user: dict[str, Any], key: str, data: dict[str, Any]) -> None:
    """Save the given prompts on this domain only (the parent's are never touched). Enabled tenants only."""
    _owned_key(user, key)
    tenant = repository.find_tenant(user["tenant_id"])
    if not user["is_admin"] and not (tenant and tenant["enabled"]):
        raise SiteError("Your account is not active yet, so prompts are read-only.", 403)
    changes = {kind: data[kind] for kind in PROMPT_TYPES if kind in data}
    if not changes:
        raise SiteError(f"Send at least one of: {', '.join(PROMPT_TYPES)}.", 400)
    for kind, text in changes.items():
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_PROMPT:
            raise SiteError(f"{kind} must be text of 1 to {MAX_PROMPT} characters.", 400)
    for kind, text in changes.items():
        upsert_prompt(key, AGENT, kind, text.strip())
