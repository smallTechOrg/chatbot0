"""
What happens when every chat model fails (rate limit, timeout, 5xx): the visitor gets a friendly "busy" reply
instead of an error, and the team hears about it on Slack, at most once an hour.
"""

import logging

from core import throttle
from summary import slack

logger = logging.getLogger(__name__)

BUSY_REPLY = (
    "Sorry, I'm getting a lot of questions right now. "
    "Please try again in a minute, or leave your email and we'll get back to you."
)

ALERT_KEY = "llm_outage"
ALERT_INTERVAL_SECONDS = 3600


class LLMUnavailable(Exception):
    """Every model failed for this message. The visitor's message is already saved; no reply was."""


def report(exc: BaseException, domain: str) -> None:
    """Log the failure, and post to Slack when no alert went out in the last hour. Never raises."""
    logger.error("[LLM_OUTAGE] every model failed for %s: %s: %s", domain, type(exc).__name__, exc)
    try:
        if throttle.claim(ALERT_KEY, ALERT_INTERVAL_SECONDS):
            slack.notify_llm_outage(f"{type(exc).__name__}: {exc}")
    except Exception:
        logger.exception("[LLM_OUTAGE] could not send the alert")
