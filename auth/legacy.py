"""The cutover lock: the old public data endpoints become admin-only when LOCK_LEGACY_API is on.

The routes stay, so an old tool gets a clear 401 or 403 instead of a 404. Matching is by URL rule, never by
path text, so nothing else can be caught by accident.
"""

from __future__ import annotations

from flask import Flask, jsonify, request

from auth.session import SAFE_METHODS, csrf_ok, current_user
from core import config

# (URL rule, methods) of every endpoint that is admin-only once the lock is on.
LOCKED: dict[str, frozenset[str]] = {
    "/chat-info": frozenset({"GET", "PATCH"}),
    "/chat-info/contact": frozenset({"PATCH"}),
    "/prompts": frozenset({"GET"}),
    "/prompt": frozenset({"POST"}),
    "/domains/": frozenset({"GET", "POST"}),
    "/domains/<int:domain_id>": frozenset({"GET"}),
}


def is_locked(rule: str | None, method: str) -> bool:
    return rule is not None and method in LOCKED.get(rule, frozenset())


def register_legacy_lock(app: Flask) -> None:
    @app.before_request
    def _lock_legacy_endpoints():
        if not config.LOCK_LEGACY_API:
            return None
        rule = request.url_rule.rule if request.url_rule else None
        if not is_locked(rule, request.method):
            return None
        user = current_user()
        if user is None:
            return jsonify({"success": False, "error": "Sign in as an admin to use this endpoint."}), 401
        if not user["is_admin"]:
            return jsonify({"success": False, "error": "Admins only."}), 403
        if request.method not in SAFE_METHODS and not csrf_ok():
            return jsonify({"success": False, "error": "Missing or wrong CSRF token."}), 403
        return None
