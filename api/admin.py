"""Admin endpoints under /api/admin: tenants (enable, trial limit, usage, users), invite/reset links, moving domains."""

from flask import Blueprint, jsonify, request

from api.guard import guarded
from api.urls import public_base
from auth.session import admin_required
from tenancy import admin

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


def _body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _link(token: str) -> str:
    return f"{public_base()}/accept/?token={token}"


@admin_api_bp.get("/tenants")
@guarded
@admin_required
def list_tenants():
    return jsonify({"tenants": admin.list_tenants()})


@admin_api_bp.patch("/tenants/<int:tenant_id>")
@guarded
@admin_required
def update_tenant(tenant_id: int):
    return jsonify({"success": True, "tenant": admin.update_tenant(tenant_id, _body())})


@admin_api_bp.post("/tenants/<int:tenant_id>/users")
@guarded
@admin_required
def add_user(tenant_id: int):
    user, token = admin.add_user(tenant_id, _body().get("email"))
    return jsonify(
        {"success": True, "user": {"id": user["id"], "email": user["email"]}, "invite_link": _link(token)}
    ), 201


@admin_api_bp.post("/users/<int:user_id>/reset-link")
@guarded
@admin_required
def reset_link(user_id: int):
    user, token = admin.reset_link_token(user_id)
    return jsonify({"success": True, "user": {"id": user["id"], "email": user["email"]}, "link": _link(token)})


@admin_api_bp.patch("/domains/<key>")
@guarded
@admin_required
def move_domain(key: str):
    admin.move_domain(key, _body().get("tenant_id"))
    return jsonify({"success": True})
