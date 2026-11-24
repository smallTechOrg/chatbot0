"""The public base URL of this service, for links people copy (invites, resets, webhook URLs)."""

from flask import request

from core import config


def public_base() -> str:
    """PUBLIC_BASE_URL if set, else the URL this request came in on."""
    if config.PUBLIC_BASE_URL:
        return config.PUBLIC_BASE_URL
    proto = request.headers.get("X-Forwarded-Proto", request.scheme).split(",")[0].strip()
    return f"{proto}://{request.host}"
