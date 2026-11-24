"""WhatsApp connections for signed-in users: /api/whatsapp/connections (list, add), /<id> (show, change, test)."""

from flask import Blueprint, jsonify, request

from api.guard import guarded
from api.urls import public_base
from auth.session import current_user, login_required
from whatsapp import management

connections_bp = Blueprint("whatsapp_connections", __name__, url_prefix="/api/whatsapp/connections")


def _body() -> dict:
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _public(connection: dict) -> dict:
    """The connection as the UI shows it, with the webhook URL to paste into the Meta app."""
    return {**connection, "webhook_url": f"{public_base()}/whatsapp/webhook/{connection['id']}"}


@connections_bp.get("")
@guarded
@login_required
def list_connections():
    user = current_user()
    return jsonify(
        {
            "connections": [_public(c) for c in management.list_connections(user)],
            "domain_keys": management.domain_keys(user),
        }
    )


@connections_bp.post("")
@guarded
@login_required
def create_connection():
    connection, check = management.create(current_user(), _body())
    return jsonify({"success": True, "connection": _public(connection), "check": check}), 201


@connections_bp.get("/<connection_id>")
@guarded
@login_required
def get_connection(connection_id: str):
    user = current_user()
    return jsonify(
        {
            "connection": _public(management.get_connection(user, connection_id)),
            "domain_keys": management.domain_keys(user),
        }
    )


@connections_bp.patch("/<connection_id>")
@guarded
@login_required
def update_connection(connection_id: str):
    check = management.update_credentials(current_user(), connection_id, _body())
    return jsonify({"success": True, "check": check})


@connections_bp.post("/<connection_id>/check")
@guarded
@login_required
def check_connection(connection_id: str):
    return jsonify({"success": True, "check": management.check(current_user(), connection_id)})


@connections_bp.post("/<connection_id>/test")
@guarded
@login_required
def test_connection(connection_id: str):
    return jsonify({"success": True, "result": management.send_test(current_user(), connection_id, _body())})
