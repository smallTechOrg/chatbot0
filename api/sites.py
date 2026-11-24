"""A tenant's websites and their prompts: /api/domains (list, add) and /api/domains/<key>/prompts (read, save)."""

import logging

from flask import Blueprint, jsonify, request

from auth.service import AuthError
from auth.session import current_user, login_required
from tenancy import sites

logger = logging.getLogger(__name__)

sites_bp = Blueprint("sites", __name__, url_prefix="/api/domains")


def _guarded(view):
    """Answer an AuthError/SiteError with its status; anything else is a logged 500."""

    def wrapper(*args, **kwargs):
        try:
            return view(*args, **kwargs)
        except AuthError as exc:
            return jsonify({"success": False, "error": exc.message}), exc.status
        except Exception:
            logger.exception("[SITES] unhandled error")
            return jsonify({"success": False, "error": "Something went wrong."}), 500

    wrapper.__name__ = view.__name__
    return wrapper


def _body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


@sites_bp.get("")
@_guarded
@login_required
def list_sites():
    return jsonify({"domains": sites.list_sites(current_user())})


@sites_bp.post("")
@_guarded
@login_required
def add_site():
    domain = sites.add_site(current_user(), _body().get("website"))
    return jsonify({"success": True, "domain": {"key": domain["key"], "address": domain["address"]}}), 201


@sites_bp.get("/<key>/prompts")
@_guarded
@login_required
def get_prompts(key: str):
    return jsonify({"prompts": sites.get_prompts(current_user(), key)})


@sites_bp.put("/<key>/prompts")
@_guarded
@login_required
def put_prompts(key: str):
    sites.set_prompts(current_user(), key, _body())
    return jsonify({"success": True})
