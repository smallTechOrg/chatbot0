"""The platform AI provider, admin only: /api/admin/ai-provider (show, save, remove) and /test. No key is returned."""

from flask import Blueprint, jsonify, request

from api.guard import guarded
from auth.session import admin_required
from tenancy import ai_provider

ai_provider_bp = Blueprint("ai_provider", __name__, url_prefix="/api/admin/ai-provider")


@ai_provider_bp.get("")
@guarded
@admin_required
def get_provider():
    return jsonify(ai_provider.status())


@ai_provider_bp.put("")
@guarded
@admin_required
def put_provider():
    data = request.get_json(silent=True)
    ai_provider.save(data if isinstance(data, dict) else {})
    return jsonify({"success": True, **ai_provider.status()})


@ai_provider_bp.delete("")
@guarded
@admin_required
def delete_provider():
    ai_provider.clear()
    return jsonify({"success": True, **ai_provider.status()})


@ai_provider_bp.post("/test")
@guarded
@admin_required
def test_provider():
    results = ai_provider.check_connection()
    return jsonify({"success": True, "ok": all(r["ok"] for r in results), "results": results})
