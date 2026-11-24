"""The Flask session for a signed-in user, the CSRF token, and the guards for API views."""

from __future__ import annotations

import functools
import hmac
import secrets
from collections.abc import Callable
from typing import Any

from flask import g, jsonify, request, session

from auth import service

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def start_session(user: dict[str, Any]) -> str:
    """Sign the user in with a fresh session (and a fresh CSRF token, which is returned)."""
    session.clear()
    session["uid"] = user["id"]
    session["sv"] = user["session_version"]
    session["csrf"] = secrets.token_urlsafe(32)
    session.permanent = True
    return session["csrf"]


def end_session() -> None:
    session.clear()


def current_user() -> dict[str, Any] | None:
    """The signed-in user, loaded once per request; None when there is no valid session."""
    if "auth_user" not in g:
        g.auth_user = service.load_session_user(session.get("uid"), session.get("sv"))
    return g.auth_user


def csrf_token() -> str:
    return session.get("csrf", "")


def csrf_ok() -> bool:
    sent = request.headers.get("X-CSRF-Token", "")
    expected = csrf_token()
    return bool(sent) and bool(expected) and hmac.compare_digest(sent, expected)


def _guard(admin: bool) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(view: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = current_user()
            if user is None:
                return jsonify({"success": False, "error": "Sign in first."}), 401
            if request.method not in SAFE_METHODS and not csrf_ok():
                return jsonify({"success": False, "error": "Missing or wrong CSRF token."}), 403
            if admin and not user["is_admin"]:
                return jsonify({"success": False, "error": "Admins only."}), 403
            return view(*args, **kwargs)

        return wrapper

    return decorator


#: A signed-in user; state-changing requests also need the X-CSRF-Token header.
login_required = _guard(admin=False)
#: A signed-in admin, same CSRF rule.
admin_required = _guard(admin=True)
