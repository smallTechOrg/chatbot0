"""Leads for signed-in users: GET /api/leads, PATCH /api/leads/<session_id>, GET /api/leads/<session_id>/history."""

import logging

from flask import Blueprint, jsonify, request

from auth.session import current_user, login_required
from leads import service
from leads.service import LeadError

logger = logging.getLogger(__name__)

leads_bp = Blueprint("leads", __name__, url_prefix="/api/leads")


def _guarded(view):
    """Answer a LeadError with its status; anything else is a logged 500."""

    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except LeadError as exc:
            return jsonify({"success": False, "error": exc.message}), exc.status
        except Exception:
            logger.exception("[LEADS] unhandled error")
            return jsonify({"success": False, "error": "Something went wrong."}), 500

    wrapper.__name__ = view.__name__
    return wrapper


@leads_bp.get("")
@_guarded
@login_required
def list_leads():
    raw = request.args.get("tenant_id")
    if raw is not None and not raw.isdigit():
        raise LeadError("tenant_id must be a number.", 400)
    return jsonify({"leads": service.list_leads(current_user(), int(raw) if raw is not None else None)})


@leads_bp.patch("/<session_id>")
@_guarded
@login_required
def patch_lead(session_id: str):
    data = request.get_json(silent=True)
    service.update_lead(current_user(), session_id, data if isinstance(data, dict) else {})
    return jsonify({"success": True})


@leads_bp.get("/<session_id>/history")
@_guarded
@login_required
def lead_history(session_id: str):
    return jsonify({"history": service.history(current_user(), session_id)})
