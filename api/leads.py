"""Leads for signed-in users: GET /api/leads, PATCH /api/leads/<session_id>, GET /api/leads/<session_id>/history."""

from flask import Blueprint, jsonify, request

from api.guard import guarded
from auth.session import current_user, login_required
from leads import service
from leads.service import LeadError

leads_bp = Blueprint("leads", __name__, url_prefix="/api/leads")


@leads_bp.get("")
@guarded
@login_required
def list_leads():
    raw = request.args.get("tenant_id")
    if raw is not None and not raw.isdigit():
        raise LeadError("tenant_id must be a number.", 400)
    return jsonify({"leads": service.list_leads(current_user(), int(raw) if raw is not None else None)})


@leads_bp.patch("/<session_id>")
@guarded
@login_required
def patch_lead(session_id: str):
    data = request.get_json(silent=True)
    service.update_lead(current_user(), session_id, data if isinstance(data, dict) else {})
    return jsonify({"success": True})


@leads_bp.get("/<session_id>/history")
@guarded
@login_required
def lead_history(session_id: str):
    return jsonify({"history": service.history(current_user(), session_id)})
