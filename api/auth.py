"""Auth endpoints under /api/auth: status, bootstrap, login, logout, me, accept (invite/reset link)."""

import functools
import logging
from typing import Any

from flask import Blueprint, current_app, jsonify, request

from api.guard import guarded
from auth import service
from auth.session import csrf_token, current_user, end_session, login_required, start_session
from tenancy import repository as tenants

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _body() -> dict[str, Any]:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _sessions_available() -> bool:
    """Sessions are signed with a key derived from CHATBOT0_SECRET_KEY; without it nobody can sign in."""
    return bool(current_app.secret_key)


def _signed_in(user: dict[str, Any]):
    return jsonify({"success": True, "user": service.public_user(user), "csrf": start_session(user)})


def _handle(view):
    """Sessions must be available (else 503), then the shared error boundary."""
    inner = guarded(view)

    @functools.wraps(view)
    def wrapper(*args: Any, **kwargs: Any):
        if not _sessions_available():
            return jsonify({"success": False, "error": "Accounts are not enabled on this server."}), 503
        return inner(*args, **kwargs)

    return wrapper


@auth_bp.get("/status")
@_handle
def status():
    return jsonify({"needs_bootstrap": service.needs_bootstrap()})


@auth_bp.post("/bootstrap")
@_handle
def bootstrap():
    data = _body()
    user = service.bootstrap(data.get("password"), data.get("email"), data.get("new_password"))
    logger.info("[AUTH] first admin created (user %s)", user["id"])
    return _signed_in(user), 201


@auth_bp.post("/login")
@_handle
def login():
    data = _body()
    return _signed_in(service.login(data.get("email"), data.get("password")))


@auth_bp.post("/logout")
@_handle
@login_required
def logout():
    user = current_user()
    if _body().get("everywhere") and user:
        service.sign_out_everywhere(user["id"])
    end_session()
    return jsonify({"success": True})


@auth_bp.post("/accept")
@_handle
def accept():
    data = _body()
    return _signed_in(service.accept_token(data.get("token"), data.get("new_password")))


@auth_bp.get("/me")
@_handle
@login_required
def me():
    user = current_user()
    tenant = tenants.find_tenant(user["tenant_id"])
    return jsonify(
        {
            "user": service.public_user(user),
            "tenant": {
                "id": tenant["id"],
                "name": tenant["name"],
                "enabled": tenant["enabled"],
                "trial_conversation_limit": tenant["trial_conversation_limit"],
                "trial_conversations_used": tenants.count_conversations(tenant["id"]),
            },
            "domains": tenants.list_domains(tenant["id"]),
            "csrf": csrf_token(),
        }
    )
