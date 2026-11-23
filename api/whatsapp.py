"""
WhatsApp Cloud API webhooks, one URL per connection (see whatsapp_connections):

GET  /whatsapp/webhook/<connection_id>  Meta's handshake when the webhook is set up.
POST /whatsapp/webhook/<connection_id>  Messages and delivery statuses, signed with
                                        that connection's app secret.

A new connection works as soon as it is saved on the admin page: the URL is
looked up in the database, nothing is configured at deploy time.

The reply is sent before the POST returns. Meta waits about 20 seconds for a
200, and a Cloud Run instance gets CPU only while a request is open, so work
moved to a background thread could freeze mid-reply. Redeliveries are dropped
by message id.
"""

import hmac
import json
import logging
from http import HTTPStatus

from flask import Blueprint, request

from core import config, crypto
from whatsapp import repository
from whatsapp.client import signature_is_valid
from whatsapp.service import handle_payload

logger = logging.getLogger(__name__)

whatsapp_bp = Blueprint("whatsapp", __name__)


def _plain(text, status):
    return text, status, {"Content-Type": "text/plain; charset=utf-8"}


@whatsapp_bp.route("/whatsapp/webhook/<connection_id>", methods=["GET"])
def verify(connection_id):
    if request.args.get("hub.mode") != "subscribe":
        return _plain("Forbidden", HTTPStatus.FORBIDDEN)
    connection = repository.get_connection(connection_id)
    token = request.args.get("hub.verify_token", "")
    if not connection or not hmac.compare_digest(token, connection["verify_token"]):
        return _plain("Forbidden", HTTPStatus.FORBIDDEN)
    return _plain(request.args.get("hub.challenge", ""), HTTPStatus.OK)


@whatsapp_bp.route("/whatsapp/webhook/<connection_id>", methods=["POST"])
def receive(connection_id):
    if not config.CHATBOT0_SECRET_KEY:
        return _plain("WhatsApp is not configured", HTTPStatus.SERVICE_UNAVAILABLE)
    try:
        connection = repository.get_connection_with_credentials(connection_id)
    except crypto.InvalidToken:
        logger.info(
            f"[WHATSAPP] connection {connection_id}: stored credentials cannot be decrypted "
            "(CHATBOT0_SECRET_KEY changed?). Re-enter them on the admin page."
        )
        return _plain("Unavailable", HTTPStatus.SERVICE_UNAVAILABLE)
    raw = request.get_data()
    if not connection or not signature_is_valid(
        raw, request.headers.get("X-Hub-Signature-256"), connection["app_secret"]
    ):
        return _plain("Forbidden", HTTPStatus.FORBIDDEN)
    try:
        payload = json.loads(raw)
    except ValueError:
        return _plain("Bad Request", HTTPStatus.BAD_REQUEST)
    if isinstance(payload, dict):
        try:
            handle_payload(connection, payload)
        except Exception:
            logger.exception("Unhandled error")
    # Always 200 once the signature is good: anything else only makes Meta retry.
    return _plain("", HTTPStatus.OK)
