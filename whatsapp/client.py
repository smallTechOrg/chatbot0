"""
The WhatsApp Cloud API (Graph API): webhook signatures, sending a text, and
checking a number's token. Every call takes the connection's own credentials:
each tenant brings their own Meta app.

Nothing here logs or returns an access token or app secret.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

import requests

from core import config

GRAPH = "https://graph.facebook.com/{version}/{path}"

# The recipient has not written in the last 24 hours: only a template may be sent.
OUTSIDE_SERVICE_WINDOW = 131047
# Access token invalid or expired.
TOKEN_ERROR_CODES = {190}


@dataclass
class GraphResult:
    ok: bool
    data: dict | None = None
    error: str | None = None
    code: int | None = None

    @property
    def token_problem(self) -> bool:
        return self.code in TOKEN_ERROR_CODES or (self.error or "").startswith("HTTP 401")


def signature_is_valid(raw_body: bytes, header: str | None, app_secret: str) -> bool:
    """Check Meta's X-Hub-Signature-256 ("sha256=<hex>") against the raw body."""
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header[len("sha256=") :])


def _call(method: str, path: str, token: str, **kwargs) -> GraphResult:
    url = GRAPH.format(version=config.WHATSAPP_GRAPH_VERSION, path=path)
    try:
        resp = requests.request(
            method,
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=config.WHATSAPP_TIMEOUT,
            **kwargs,
        )
    except requests.RequestException as exc:
        return GraphResult(False, error=f"network error: {type(exc).__name__}")
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code >= 400:
        err = body.get("error") or {}
        code = err.get("code")
        message = err.get("error_user_msg") or err.get("message") or resp.text[:200]
        return GraphResult(False, data=body, error=f"HTTP {resp.status_code}: {message}"[:500], code=code)
    return GraphResult(True, data=body)


def send_text(phone_number_id: str, token: str, to: str, body: str) -> GraphResult:
    """Send one text message from the business number to *to* (the user's wa_id)."""
    return _call(
        "POST",
        f"{phone_number_id}/messages",
        token,
        json={
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        },
    )


def check_number(phone_number_id: str, token: str) -> GraphResult:
    """Read the number's display number and verified name: proves the token works for it."""
    return _call("GET", phone_number_id, token, params={"fields": "display_phone_number,verified_name"})
