"""A tenant's own Slack incoming webhook: store it encrypted, say whether it is set, send a test message."""

from __future__ import annotations

import logging
from typing import Any

from core import crypto
from core.errors import ServiceError
from summary import slack
from tenancy import repository

logger = logging.getLogger(__name__)

# Slack incoming webhooks live here. Anything else is refused, so a tenant cannot make the server post to
# an arbitrary address (and a pasted secret of another kind is not stored).
WEBHOOK_PREFIX = "https://hooks.slack.com/services/"
MAX_URL_LENGTH = 300


class SlackSettingsError(ServiceError):
    """A request the API answers with `status` and a message that is safe to show."""


def _tenant_for(user: dict[str, Any]) -> dict[str, Any]:
    tenant = repository.find_tenant(user["tenant_id"])
    if tenant is None:
        raise SlackSettingsError("No such account.", 404)
    return tenant


def _require_enabled(user: dict[str, Any]) -> dict[str, Any]:
    tenant = _tenant_for(user)
    if not tenant["enabled"]:
        raise SlackSettingsError("Slack notifications are available once your account is enabled.", 403)
    return tenant


def status(user: dict[str, Any]) -> dict[str, Any]:
    """Only whether a webhook is set. The URL is never shown back."""
    tenant = _tenant_for(user)
    return {"configured": repository.get_slack_webhook(tenant["id"]) is not None, "enabled": tenant["enabled"]}


def save(user: dict[str, Any], url: Any) -> None:
    tenant = _require_enabled(user)
    if not isinstance(url, str) or not url.strip().startswith(WEBHOOK_PREFIX) or len(url.strip()) > MAX_URL_LENGTH:
        raise SlackSettingsError(f"Enter a Slack incoming webhook URL (it starts with {WEBHOOK_PREFIX}).", 422)
    repository.set_slack_webhook(tenant["id"], crypto.encrypt(url.strip()))


def clear(user: dict[str, Any]) -> None:
    repository.set_slack_webhook(_tenant_for(user)["id"], None)


def webhook_for(tenant_id: int) -> str | None:
    """The plain webhook URL, for sending only. None when not set or unreadable (the key changed)."""
    encrypted = repository.get_slack_webhook(tenant_id)
    if encrypted is None:
        return None
    try:
        return crypto.decrypt(encrypted)
    except crypto.InvalidToken:
        logger.error("[SLACK] tenant %s: the stored webhook cannot be decrypted; it must be entered again", tenant_id)
        return None


def send_test(user: dict[str, Any]) -> None:
    tenant = _require_enabled(user)
    url = webhook_for(tenant["id"])
    if url is None:
        raise SlackSettingsError("Save a Slack webhook first.", 409)
    try:
        slack.post_to_slack(
            {"username": slack.SENDER, "text": "chatbot0: this is a test message. Slack is connected."}, url
        )
    except Exception as exc:
        # Log the type only: a connection error's text can contain the webhook URL.
        logger.warning("[SLACK] tenant %s: test message failed (%s)", tenant["id"], type(exc).__name__)
        raise SlackSettingsError("Slack did not accept the message. Check the webhook URL.", 502) from None
