"""A tenant's Slack webhook: /api/slack (status, save, clear) and /api/slack/test. The URL is never returned."""

from flask import Blueprint, jsonify, request

from api.guard import guarded
from auth.session import current_user, login_required
from tenancy import slack_settings

slack_bp = Blueprint("slack_settings", __name__, url_prefix="/api/slack")


@slack_bp.get("")
@guarded
@login_required
def get_status():
    return jsonify(slack_settings.status(current_user()))


@slack_bp.put("")
@guarded
@login_required
def put_webhook():
    data = request.get_json(silent=True)
    slack_settings.save(current_user(), data.get("webhook_url") if isinstance(data, dict) else None)
    return jsonify({"success": True, "configured": True})


@slack_bp.delete("")
@guarded
@login_required
def delete_webhook():
    slack_settings.clear(current_user())
    return jsonify({"success": True, "configured": False})


@slack_bp.post("/test")
@guarded
@login_required
def test_webhook():
    slack_settings.send_test(current_user())
    return jsonify({"success": True})
