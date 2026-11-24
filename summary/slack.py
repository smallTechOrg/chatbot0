"""
Post the periodic chat summary to Slack through an incoming webhook.
One line per conversation ("7th Oct, 4:13 pm - SMALLTECH - Anjali - summary"); LLM failures
become one sentence at the end, and silent sessions are left out.
"""

import logging
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import requests

from core import config

logger = logging.getLogger(__name__)

# Slack accepts about 40,000 characters in ``text``. Stay well under it and
# split a long run into several messages.
MESSAGE_LIMIT = 30_000
# Longest single conversation line.
LINE_LIMIT = 3_000

TITLE = "chatbot0 Summary"
# Shown as the sender when the webhook honours it (legacy incoming webhooks do;
# a Slack-app webhook uses the app's own display name, set in the app config).
SENDER = "chatbot0-updates"
# Separates distinct LLM errors in the failure sentence when a run saw more
# than one kind.
ERROR_SEPARATOR = "; "


def send_summaries_to_slack(result: dict[str, Any]) -> dict[str, Any]:
    """
    Send the whole summary. Returns {"sent": n, "skipped": reason?}.
    Nothing is sent when there are no sessions, only silent sessions, or no
    webhook. Raises if a post fails, so the caller can record it.
    """
    if not result.get("sessions"):
        logger.warning("[SLACK] No sessions waiting for a summary. Skipping Slack delivery.")
        return {"sent": 0, "skipped": "no sessions"}

    if not config.SLACK_WEBHOOK_URL:
        logger.warning("[SLACK] SLACK_WEBHOOK_URL is not set. Skipping Slack delivery.")
        return {"sent": 0, "skipped": "SLACK_WEBHOOK_URL not set"}

    messages = build_messages(result)
    if not messages:
        logger.warning("[SLACK] Only silent sessions in this run. Skipping Slack delivery.")
        return {"sent": 0, "skipped": "nothing to report"}

    for payload in messages:
        post_to_slack(payload)
    logger.info(f"[SLACK] Sent {len(messages)} message(s) to Slack.")
    return {"sent": len(messages)}


def build_messages(result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Turn a periodic_summary() result into webhook payloads. Normally one; a very
    long run is split, and each part repeats the header. Sessions whose LLM
    call failed become one sentence at the end instead of a line each.
    """
    sessions = result.get("sessions", [])
    if not sessions:
        return []

    # Silent sessions are not reported and do not count towards "all failed".
    reportable = [s for s in sessions if not s.get("silent")]
    llm_failed = [s for s in reportable if "llm_error" in s]
    lines = [_conversation_line(s) for s in reportable if "llm_error" not in s]
    if llm_failed:
        lines.append(_llm_failure_line(llm_failed, len(reportable)))
    if not lines:
        return []

    header = _header(result)

    messages: list[dict[str, Any]] = []
    current = [header]
    size = len(header)
    for line in lines:
        if size + len(line) + 1 > MESSAGE_LIMIT and len(current) > 1:
            messages.append(_payload(current))
            current = [header]
            size = len(header)
        current.append(line)
        size += len(line) + 1
    messages.append(_payload(current))
    return messages


def _payload(lines: list[str]) -> dict[str, Any]:
    return {"username": SENDER, "text": "\n".join(lines)}


def post_to_slack(payload: dict[str, Any], webhook_url: str | None = None) -> None:
    """POST one payload to the webhook. Raises on a non-2xx answer."""
    url = webhook_url or config.SLACK_WEBHOOK_URL
    response = requests.post(url, json=payload, timeout=config.SLACK_TIMEOUT)
    if not response.ok:
        raise RuntimeError(f"Slack webhook returned {response.status_code}: {response.text[:200]}")


def notify_signup(address: str, contact: dict[str, Any] | None = None) -> bool:
    """
    Post one line about a new chatbot0 sign-up to the same channel:
    "New chatbot0 sign-up: acme.com - Anjali - anjali@acme.com".
    Returns whether it was sent. Never raises: a Slack problem must not fail
    the sign-up, which is already saved.
    """
    if not config.SLACK_WEBHOOK_URL:
        logger.warning("[SLACK] SLACK_WEBHOOK_URL is not set. Skipping the sign-up message.")
        return False
    try:
        post_to_slack({"username": SENDER, "text": build_signup_text(address, contact)})
        return True
    except Exception as exc:
        logger.error(f"[SLACK] Sign-up message for {address} failed: {exc}")
        return False


def notify_whatsapp_problem(connection: dict[str, Any], error: str) -> bool:
    """
    One line when a WhatsApp connection starts failing, e.g. an expired token:
    "WhatsApp needs attention: ACME (+1 555...) - HTTP 401: ...". Never raises.
    """
    if not config.SLACK_WEBHOOK_URL:
        logger.warning("[SLACK] SLACK_WEBHOOK_URL is not set. Skipping the WhatsApp alert.")
        return False
    number = connection.get("display_number") or connection.get("phone_number_id")
    text = (
        f"*WhatsApp needs attention:* {_escape(str(connection.get('domain_key', '')).upper())} "
        f"({_escape(str(number))}) - {_escape(_clip(error, 300))}"
    )
    label = config.environment_label()
    try:
        post_to_slack({"username": SENDER, "text": f"*[{label}]* {text}" if label else text})
        return True
    except Exception as exc:
        logger.error(f"[SLACK] WhatsApp alert failed: {exc}")
        return False


def notify_llm_outage(error: str) -> bool:
    """
    One line when every chat model fails: "Chat is degraded: ... - RateLimitError: ...". The caller limits how
    often this is sent. Never raises.
    """
    if not config.SLACK_WEBHOOK_URL:
        logger.warning("[SLACK] SLACK_WEBHOOK_URL is not set. Skipping the LLM outage alert.")
        return False
    text = f"*Chat is degraded:* every LLM model failed, visitors see the busy message. {_escape(_clip(error, 300))}"
    label = config.environment_label()
    try:
        post_to_slack({"username": SENDER, "text": f"*[{label}]* {text}" if label else text})
        return True
    except Exception as exc:
        logger.error(f"[SLACK] LLM outage alert failed: {exc}")
        return False


def build_signup_text(address: str, contact: dict[str, Any] | None = None) -> str:
    contact = contact or {}
    parts = [_escape(address)]
    for name in ("contact_name", "email", "mobile"):
        value = (contact.get(name) or "").strip()
        if value:
            parts.append(_escape(value))
    if len(parts) == 1:
        parts.append("no contact details")
    text = "*New chatbot0 sign-up:* " + " - ".join(parts)
    label = config.environment_label()
    return f"*[{label}]* {text}" if label else text


def _header(result: dict[str, Any]) -> str:
    run_at: datetime | None = result.get("run_at")
    title = TITLE
    if isinstance(run_at, datetime):
        title = f"{TITLE} - {format_header_time(run_at)}"
    # Slack link syntax: <url|text>. Incoming webhooks render it by default.
    link = f"<{config.DASHBOARD_URL}|{title}>"
    # Staging and local runs post to the same channel; mark them so nobody
    # mistakes a test conversation for a lead.
    label = config.environment_label()
    return f"*[{label}]* {link}" if label else link


def format_header_time(value: datetime) -> str:
    """7th Oct 2026 - 5 pm IST"""
    value = _localize(value)
    return f"{_ordinal(value.day)} {value.strftime('%b %Y')} - {_clock(value)} {value.strftime('%Z')}"


def _conversation_line(session: dict[str, Any]) -> str:
    first = session.get("first_message")
    when = format_line_time(first) if isinstance(first, datetime) else "unknown time"

    domain = (session.get("domain") or "UNKNOWN").upper()
    if session.get("channel") == "whatsapp":
        domain += " (WhatsApp)"
    name = (session.get("name") or "").strip() or "Unknown"

    if "error" in session:
        body = f"summary failed ({session['error']})"
    else:
        body = (session.get("summary") or "no summary").replace("\n", " ").strip()

    line = f"{when} - {domain} - {_escape(name)} - {_escape(body)}"
    return _clip(line, LINE_LIMIT)


def format_line_time(value: datetime) -> str:
    """7th Oct, 4:13 pm"""
    value = _localize(value)
    return f"{_ordinal(value.day)} {value.strftime('%b')}, {_clock(value)}"


def _llm_failure_line(failed: list[dict[str, Any]], total: int) -> str:
    """
    One sentence for the sessions whose LLM call failed. Distinct errors are
    listed once each, in the order they were first seen. The count is only
    shown when the run also had conversations that worked.
    """
    errors: list[str] = []
    for session in failed:
        error = str(session.get("llm_error") or "unknown error")
        if error not in errors:
            errors.append(error)

    if len(failed) == total:
        what = "Failed to generate a summary."
    elif len(failed) == 1:
        what = "Failed to generate a summary for 1 conversation."
    else:
        what = f"Failed to generate a summary for {len(failed)} conversations."
    line = f"{what} LLM calls failed with error: {_escape(ERROR_SEPARATOR.join(errors))}."
    return _clip(line, LINE_LIMIT)


def _localize(value: datetime) -> datetime:
    """
    Put a timestamp in the display timezone. A naive value is taken to be in
    that timezone already; an aware one (TIMESTAMPTZ from the database) is
    converted.
    """
    tz = ZoneInfo(config.PERIODIC_SUMMARY_TIMEZONE)
    if value.tzinfo is None:
        return value.replace(tzinfo=tz)
    return value.astimezone(tz)


def _clock(value: datetime) -> str:
    """4:13 pm. Whole hours drop the minutes: 5 pm."""
    hour = value.strftime("%I").lstrip("0")
    ampm = value.strftime("%p").lower()
    if value.minute == 0:
        return f"{hour} {ampm}"
    return f"{hour}:{value.minute:02d} {ampm}"


def _ordinal(day: int) -> str:
    suffix = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _escape(text: str) -> str:
    """Slack reads &, < and > as markup in text. Escape them."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
