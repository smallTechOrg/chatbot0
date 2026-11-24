"""
Handle one WhatsApp webhook delivery for one connection: answer each message
with the same chat engine the web widget uses.

A WhatsApp chat is identified by (business number, sender). The connection
picks the domain, so prompts follow the domain hierarchy as on the web. Chats
are pull-only: the customer writes first, so free-form replies are allowed
(WhatsApp's 24-hour service window).
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterator

from chat.engine import get_groq_response
from chat.outage import BUSY_REPLY, LLMUnavailable
from core.config import agent_type
from summary.slack import notify_whatsapp_problem
from tenancy import service as tenancy
from whatsapp import repository
from whatsapp.client import GraphResult, send_text
from whatsapp.formatting import split_message, to_whatsapp

logger = logging.getLogger(__name__)

# WhatsApp chats use the sales agent: the lead details it captures are the point.
REQUEST_TYPE = agent_type.SALES.value

# Fixed namespace: a sender keeps their session across restarts and deploys.
_SESSION_NAMESPACE = uuid.UUID("5d1c1d8e-6a52-4a39-9d52-7b2f3a1e9c11")

FALLBACK_REPLY = "Sorry, something went wrong on our side. Please send your message again in a moment."
TEXT_ONLY_REPLY = "Sorry, I can only read text messages for now. Please type your question."

# Message types that get TEXT_ONLY_REPLY. Others (reaction, system, ...) are ignored.
_MEDIA_TYPES = {"image", "audio", "voice", "video", "document", "sticker", "location", "contacts", "unsupported"}


def session_id_for(phone_number_id: str, wa_id: str) -> str:
    """The chat session for one sender talking to one business number (a UUID, like web sessions)."""
    return str(uuid.uuid5(_SESSION_NAMESPACE, f"{phone_number_id}:{wa_id}"))


def _message_text(msg: dict) -> str | None:
    kind = msg.get("type")
    if kind == "text":
        return (msg.get("text") or {}).get("body")
    if kind == "button":  # a quick-reply button on a template
        return (msg.get("button") or {}).get("text")
    if kind == "interactive":
        inter = msg.get("interactive") or {}
        reply = inter.get("button_reply") or inter.get("list_reply") or {}
        return reply.get("title")
    return None


def iter_events(payload: dict) -> Iterator[dict]:
    """
    Yield one event per message or delivery status in a webhook payload:
      {"kind": "text", phone_number_id, wa_id, name, message_id, text}
      {"kind": "media", phone_number_id, wa_id, message_id, type}
      {"kind": "failed_status", phone_number_id, error}
    """
    if payload.get("object") != "whatsapp_business_account":
        return
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            if change.get("field") != "messages":
                continue
            value = change.get("value") or {}
            pnid = (value.get("metadata") or {}).get("phone_number_id")
            if not pnid:
                continue
            names = {c.get("wa_id"): (c.get("profile") or {}).get("name") for c in value.get("contacts") or []}
            for msg in value.get("messages") or []:
                wa_id, mid = msg.get("from"), msg.get("id")
                if not (wa_id and mid):
                    continue
                text = (_message_text(msg) or "").strip()
                if text:
                    yield {
                        "kind": "text",
                        "phone_number_id": pnid,
                        "wa_id": wa_id,
                        "name": names.get(wa_id),
                        "message_id": mid,
                        "text": text,
                    }
                elif msg.get("type") in _MEDIA_TYPES:
                    yield {
                        "kind": "media",
                        "phone_number_id": pnid,
                        "wa_id": wa_id,
                        "message_id": mid,
                        "type": msg.get("type"),
                    }
            for status in value.get("statuses") or []:
                if status.get("status") == "failed":
                    errs = status.get("errors") or [{}]
                    err = errs[0]
                    detail = (err.get("error_data") or {}).get("details") or err.get("message") or err.get("title")
                    yield {
                        "kind": "failed_status",
                        "phone_number_id": pnid,
                        "error": f"delivery failed ({err.get('code')}): {detail}",
                    }


def handle_payload(connection: dict, payload: dict) -> None:
    """
    Handle every event in a payload verified against *connection*'s app
    secret. One Meta app can carry several numbers to the same webhook: an
    event for another number is handled only when that number is connected
    with the same app secret. One bad event never stops the rest.
    """
    for event in iter_events(payload):
        try:
            conn = connection
            if event["phone_number_id"] != connection["phone_number_id"]:
                conn = repository.get_connection_by_number(event["phone_number_id"])
                if not conn or conn["app_secret"] != connection["app_secret"]:
                    logger.info(f"[WHATSAPP] event for unconnected number {event['phone_number_id']}; ignoring")
                    continue
            if event["kind"] == "failed_status":
                _record_failure(conn, event["error"], token_problem=False)
                continue
            repository.mark_inbound(conn["id"])
            if not repository.claim_message(event["message_id"]):
                logger.info(f"[WHATSAPP] message {event['message_id']} already handled; ignoring the redelivery")
                continue
            if event["kind"] == "media":
                _send(conn, event["wa_id"], [TEXT_ONLY_REPLY])
            else:
                handle_text(conn, event["wa_id"], event["name"], event["text"])
        except Exception:
            logger.exception(f"[WHATSAPP] failed handling {event['kind']} event")


def handle_text(conn: dict, wa_id: str, name: str | None, text: str) -> None:
    session_id = session_id_for(conn["phone_number_id"], wa_id)
    domain = conn["domain_key"]
    try:
        if tenancy.conversation_allowed(domain, session_id):
            repository.ensure_chat_info(session_id, domain, REQUEST_TYPE, f"+{wa_id}", name)
            reply = get_groq_response(text, session_id, REQUEST_TYPE, domain)
        else:
            reply = tenancy.TRIAL_LIMIT_REPLY  # defence in depth: WhatsApp is also locked for disabled tenants
        bodies = split_message(to_whatsapp(reply)) or [FALLBACK_REPLY]
    except LLMUnavailable:
        bodies = [BUSY_REPLY]  # already logged and alerted by the engine
    except Exception:
        logger.exception("Unhandled error")
        bodies = [FALLBACK_REPLY]
    _send(conn, wa_id, bodies)


def _send(conn: dict, wa_id: str, bodies: list[str]) -> bool:
    for body in bodies:
        result = send_text(conn["phone_number_id"], conn["access_token"], wa_id, body)
        if not result.ok:
            # Any error Meta answers with (bad token, recipient not allowed,
            # rate limit) needs a person; a network blip does not.
            _record_failure(
                conn, result.error or "send failed", token_problem=result.token_problem or result.code is not None
            )
            return False
    return True


def _record_failure(conn: dict, error: str, token_problem: bool) -> None:
    """
    Save the error on the connection. A problem a person must fix flags the
    connection 'needs attention'; Slack hears about it once, when it is first flagged, not
    on every failed message after.
    """
    logger.error(f"[WHATSAPP] connection {conn['id']}: {error}")
    newly_flagged = repository.mark_error(conn["id"], error, needs_attention=token_problem)
    if newly_flagged:
        notify_whatsapp_problem(conn, error)


__all__ = ["GraphResult", "handle_payload", "iter_events", "session_id_for"]
