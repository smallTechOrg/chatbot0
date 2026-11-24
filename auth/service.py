"""Auth rules: password length, login rate limit, bootstrap of the first admin, invite and reset tokens."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import timedelta
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from auth import repository
from core import config
from core.errors import ServiceError
from core.schema import SMALLTECH_TENANT
from tenancy import repository as tenants

MIN_PASSWORD_LENGTH = 10
MAX_FAILED_LOGINS = 10
LOGIN_WINDOW = timedelta(minutes=15)
TOKEN_LIFETIME = {"invite": timedelta(days=7), "reset": timedelta(hours=24)}

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_dummy_hash: str | None = None


class AuthError(ServiceError):
    """An auth request the API answers with `status` and a message that is safe to show."""


def normalize_email(email: Any) -> str:
    value = email.strip().lower() if isinstance(email, str) else ""
    if len(value) > 254 or not _EMAIL.match(value):
        raise AuthError("Enter a valid email address.", 400)
    return value


def validate_password(password: Any) -> str:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Use at least {MIN_PASSWORD_LENGTH} characters for the password.", 400)
    return password


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _burn_hash_time(password: str) -> None:
    """Spend the time of a real check, so an unknown email answers as slowly as a wrong password."""
    global _dummy_hash
    if _dummy_hash is None:
        _dummy_hash = generate_password_hash("not-a-real-password")
    check_password_hash(_dummy_hash, password)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {"id": user["id"], "email": user["email"], "is_admin": user["is_admin"], "tenant_id": user["tenant_id"]}


def needs_bootstrap() -> bool:
    return not repository.admin_exists()


def login(email: Any, password: Any) -> dict[str, Any]:
    """The user for these credentials. Wrong email and wrong password look the same."""
    wrong = AuthError("Wrong email or password.", 401)
    try:
        address = normalize_email(email)
    except AuthError:
        raise wrong from None
    if repository.count_recent_failures(address, LOGIN_WINDOW) >= MAX_FAILED_LOGINS:
        raise AuthError("Too many failed attempts. Try again in a few minutes.", 429)

    user = repository.find_user_by_email(address)
    stored = user["password_hash"] if user else None
    candidate = password if isinstance(password, str) else ""
    if not stored:
        _burn_hash_time(candidate)
    if not (user and stored and check_password_hash(stored, candidate)):
        repository.record_failed_attempt(address)
        raise wrong
    repository.clear_attempts(address)
    repository.touch_login(user["id"])
    return user


def bootstrap(shared_password: Any, email: Any, new_password: Any) -> dict[str, Any]:
    """Create the first admin (smallTech tenant). Only while no admin exists, with the shared setup password."""
    if not config.CHATBOT0_ADMIN_PASSWORD:
        raise AuthError("Setup is not enabled on this server.", 503)
    if repository.admin_exists():
        raise AuthError("Setup is already done.", 409)
    supplied = shared_password if isinstance(shared_password, str) else ""
    if not hmac.compare_digest(supplied.encode(), config.CHATBOT0_ADMIN_PASSWORD.encode()):
        raise AuthError("Wrong setup password.", 403)
    address = normalize_email(email)
    password = validate_password(new_password)
    tenant = tenants.find_tenant_by_name(SMALLTECH_TENANT)
    if tenant is None:
        raise AuthError("The smallTech tenant is missing.", 503)
    user = repository.create_first_admin(tenant["id"], address, generate_password_hash(password))
    if user is None:
        raise AuthError("Setup is already done.", 409)
    return user


def issue_token(user_id: int, purpose: str) -> str:
    """A new single-use invite or reset token (shown once, stored only as a hash)."""
    token = secrets.token_urlsafe(32)
    repository.insert_token(hash_token(token), user_id, purpose, TOKEN_LIFETIME[purpose])
    return token


def accept_token(token: Any, new_password: Any) -> dict[str, Any]:
    """Set the password from an invite or reset token. The token dies, and so does every other session."""
    password = validate_password(new_password)
    invalid = AuthError("This link is invalid or has expired.", 400)
    if not isinstance(token, str) or not token:
        raise invalid
    user_id = repository.consume_token(hash_token(token))
    if user_id is None:
        raise invalid
    repository.set_password(user_id, generate_password_hash(password))
    repository.touch_login(user_id)
    user = repository.find_user(user_id)
    if user is None:
        raise invalid
    return user


def load_session_user(user_id: Any, session_version: Any) -> dict[str, Any] | None:
    """The user a session cookie names, if the cookie is still valid (the session version has not moved on)."""
    if not isinstance(user_id, int) or not isinstance(session_version, int):
        return None
    user = repository.find_user(user_id)
    if user is None or user["session_version"] != session_version:
        return None
    return user


def sign_out_everywhere(user_id: int) -> None:
    repository.bump_session_version(user_id)
