"""Cleaning and checking what people paste into the WhatsApp connection forms."""

from __future__ import annotations

import re
import unicodedata

from whatsapp.client import OUTSIDE_SERVICE_WINDOW

PHONE_NUMBER_ID = re.compile(r"^\d{5,20}$")
RECIPIENT = re.compile(r"^\+?\d{7,15}$")

# Graph API codes with a known fix, shown next to a failed test message.
SEND_HINTS = {
    OUTSIDE_SERVICE_WINDOW: "The recipient has not messaged this number in the last 24 hours. "
    "Send any message to the business number from that phone first, then retry.",
    131030: "On a Meta test number, only recipients added under API Setup > 'To' can receive messages.",
    190: "The access token is invalid or expired. Replace it below.",
}


def clean(value: str) -> str:
    """
    A pasted value without the invisible characters web pages copy along:
    any Unicode space (non-breaking, thin, ...) and format characters such as
    left-to-right marks and zero-width spaces, which the Meta dashboard adds.
    """
    return "".join(ch for ch in value if not (ch.isspace() or unicodedata.category(ch) in ("Cf", "Zs")))


def clean_id(value: str) -> str:
    """A pasted numeric ID: invisible characters dropped, a leading "ID:" label too."""
    value = clean(value)
    value = re.sub(r"^(phone ?number ?)?id:?", "", value, flags=re.I)
    # Unicode digits (e.g. full-width) to ASCII.
    return "".join(str(unicodedata.digit(ch)) if ch.isdigit() else ch for ch in value)
