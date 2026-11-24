"""
Per-tenant Slack delivery of the periodic summary: each tenant that stored a webhook gets the new summaries of its
own leads, formatted exactly like the global channel's message. A lead reaches only the webhook of the tenant that
owns its domain key; the global channel (send_summaries_to_slack) still receives everything.
"""

import logging
from typing import Any

from summary.slack import build_messages, post_to_slack
from tenancy import repository
from tenancy.slack_settings import webhook_for

logger = logging.getLogger(__name__)


def send_tenant_summaries(result: dict[str, Any]) -> dict[int, int]:
    """
    Post this run's new summaries to each tenant's own webhook. Returns {tenant_id: messages sent}.
    Summaries that are only being resent because the global channel missed them are skipped (the tenant already
    had them when they were first made), and one tenant's failure never affects another. Never raises.
    """
    try:
        return _deliver(result)
    except Exception:
        logger.exception("[SLACK] per-tenant delivery failed")
        return {}


def _deliver(result: dict[str, Any]) -> dict[int, int]:
    fresh = [s for s in result.get("sessions", []) if not s.get("resent") and s.get("domain")]
    if not fresh:
        return {}
    routes = repository.slack_routes(sorted({s["domain"] for s in fresh}))
    by_tenant: dict[int, list[dict[str, Any]]] = {}
    for session in fresh:
        route = routes.get(session["domain"])
        if route:
            by_tenant.setdefault(route[0], []).append(session)

    sent: dict[int, int] = {}
    for tenant_id, sessions in by_tenant.items():
        messages = build_messages({**result, "sessions": sessions})
        url = webhook_for(tenant_id) if messages else None
        if not url:
            continue
        try:
            for payload in messages:
                post_to_slack(payload, url)
            sent[tenant_id] = len(messages)
        except Exception as exc:
            # Type only: a connection error's text can contain the webhook URL.
            logger.error("[SLACK] tenant %s: delivery failed (%s)", tenant_id, type(exc).__name__)
    return sent
