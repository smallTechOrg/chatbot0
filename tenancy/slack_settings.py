"""A tenant's own Slack incoming webhook: store it encrypted, say whether it is set, send a test message."""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import urlparse

from core import crypto
from core.errors import ServiceError
from summary import slack
from tenancy import repository

logger = logging.getLogger(__name__)

# Slack incoming webhooks live here. Anything else is refused, so a tenant cannot make the server post to
# an arbitrary address (and a pasted secret of another kind is not stored).
WEBHOOK_PREFIX = "https://hooks.slack.com/services/"
MAX_URL_LENGTH = 300
#: Where the header of a tenant's Slack summary links to until the tenant enters its own link.
DEFAULT_DASHBOARD_LINK = "https://chatbot0.smalltech.in/dashboard/"


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
    """What the settings page shows. The webhook URL is never included, only whether one is set."""
    tenant = _tenant_for(user)
    prefs = repository.get_slack_prefs(tenant["id"]) or {}
    return {
        "enabled": tenant["enabled"],
        "configured": bool(prefs.get("configured")),
        "notifications_on": bool(prefs.get("notifications_on", True)),
        "dashboard_url": prefs.get("dashboard_url") or DEFAULT_DASHBOARD_LINK,
        "dashboard_url_is_default": not prefs.get("dashboard_url"),
        "default_dashboard_url": DEFAULT_DASHBOARD_LINK,
    }


def _check_https_url(raw: Any) -> str:
    """An https URL with a host, no spaces and none of the characters Slack reads as link markup."""
    url = raw.strip() if isinstance(raw, str) else ""
    parsed = urlparse(url)
    bad = (not url, len(url) > MAX_URL_LENGTH, parsed.scheme != "https", not parsed.hostname)
    if any(bad) or re.search(r"[\s<>|]", url):
        raise SlackSettingsError("Enter the dashboard link as a full https:// address.", 422)
    return url


def save(user: dict[str, Any], data: dict[str, Any]) -> None:
    """
    Change any of: webhook_url (a Slack incoming webhook), notifications_on (true/false) and dashboard_url
    (an https address; "" goes back to the default). Fields that are left out stay as they are.
    """
    tenant = _require_enabled(user)
    webhook = data.get("webhook_url")
    if webhook is not None:
        if (
            not isinstance(webhook, str)
            or not webhook.strip().startswith(WEBHOOK_PREFIX)
            or len(webhook) > MAX_URL_LENGTH
        ):
            raise SlackSettingsError(f"Enter a Slack incoming webhook URL (it starts with {WEBHOOK_PREFIX}).", 422)
        if re.search(r"\s", webhook.strip()):
            raise SlackSettingsError("The webhook URL must not contain spaces.", 422)
    on = data.get("notifications_on")
    if on is not None and not isinstance(on, bool):
        raise SlackSettingsError("notifications_on must be true or false.", 422)
    link = data.get("dashboard_url")
    clear_link = link is not None and link == ""
    new_link = None if link is None or clear_link else _check_https_url(link)
    if webhook is None and on is None and link is None:
        raise SlackSettingsError("Send webhook_url, notifications_on or dashboard_url.", 400)
    if webhook is not None:
        repository.set_slack_webhook(tenant["id"], crypto.encrypt(webhook.strip()))
    repository.set_slack_prefs(tenant["id"], on, new_link, clear_link)


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
