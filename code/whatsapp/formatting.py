"""
Turn the markdown the prompts ask the model for into WhatsApp's own markup.

WhatsApp: *bold*, _italic_, ~strike~, ```mono```, "- " and "1. " lists, "> " quotes.
It has no headings and no links syntax, so "**x**" and "## x" would show as
literal characters.
"""
from __future__ import annotations

import re

# WhatsApp rejects a text body over 4096 characters.
MAX_BODY = 4096

# Placeholders, so a converted bold's "*" is not read again as italic.
_BOLD_OPEN, _BOLD_CLOSE = "\x01", "\x02"

_FENCE = re.compile(r"```.*?```", re.S)
_HEADING = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+(.+?)[ \t]*#*[ \t]*$", re.M)
_BOLD = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1", re.S)
_ITALIC_STAR = re.compile(r"(?<![\*\w])\*(?=[^\s\*])([^\n\*]+?)(?<=[^\s\*])\*(?![\*\w])")
_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+)\)")
_STAR_BULLET = re.compile(r"^([ \t]*)[\*\+][ \t]+", re.M)
_RULE = re.compile(r"^[ \t]*([-*_])([ \t]*\1){2,}[ \t]*$", re.M)


def to_whatsapp(text: str) -> str:
    """Convert markdown *text* to WhatsApp formatting. Code fences are kept."""
    fences: list[str] = []

    def stash(match: re.Match) -> str:
        fences.append(match.group(0))
        return f"\x03{len(fences) - 1}\x03"

    text = _FENCE.sub(stash, text.replace("\r\n", "\n"))

    text = _RULE.sub("", text)
    text = _HEADING.sub(lambda m: f"{_BOLD_OPEN}{m.group(1)}{_BOLD_CLOSE}", text)
    text = _BOLD.sub(lambda m: f"{_BOLD_OPEN}{m.group(2)}{_BOLD_CLOSE}", text)
    # "* item" bullets must not be read as the start of an italic span.
    text = _STAR_BULLET.sub(lambda m: f"{m.group(1)}- ", text)
    text = _ITALIC_STAR.sub(lambda m: f"_{m.group(1)}_", text)
    text = _LINK.sub(lambda m: m.group(1) if m.group(1) == m.group(2) else f"{m.group(1)} ({m.group(2)})", text)
    text = text.replace(_BOLD_OPEN, "*").replace(_BOLD_CLOSE, "*")

    text = re.sub(r"\x03(\d+)\x03", lambda m: fences[int(m.group(1))], text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_message(text: str, limit: int = MAX_BODY) -> list[str]:
    """Split *text* into bodies of at most *limit* characters, on paragraph or line breaks where it can."""
    text = text.strip()
    if not text:
        return []
    parts: list[str] = []
    while len(text) > limit:
        cut = max(text.rfind("\n\n", 0, limit), text.rfind("\n", 0, limit), text.rfind(" ", 0, limit))
        if cut < limit // 2:  # no break near the end: hard cut
            cut = limit
        parts.append(text[:cut].rstrip())
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts
