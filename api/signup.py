"""POST /api/signup: a new account (a disabled tenant, its user and its first website), signed in at once."""

import logging

from flask import Blueprint, current_app, jsonify, request

from auth import service as auth
from auth.service import AuthError
from auth.session import start_session
from tenancy import sites

logger = logging.getLogger(__name__)

signup_bp = Blueprint("signup", __name__, url_prefix="/api")


@signup_bp.post("/signup")
def signup():
    if not current_app.secret_key:
        return jsonify({"success": False, "error": "Accounts are not enabled on this server."}), 503
    data = request.get_json(silent=True)
    try:
        user, domain = sites.sign_up(data if isinstance(data, dict) else {})
    except AuthError as exc:
        return jsonify({"success": False, "error": exc.message}), exc.status
    except Exception:
        logger.exception("[SIGNUP] unhandled error")
        return jsonify({"success": False, "error": "Something went wrong."}), 500
    csrf = start_session(user)
    return (
        jsonify(
            {
                "success": True,
                "user": auth.public_user(user),
                "csrf": csrf,
                "domain": {"key": domain["key"], "address": domain["address"]},
            }
        ),
        201,
    )
