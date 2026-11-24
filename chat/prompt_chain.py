"""
Where each prompt of a domain comes from: the parent chain and, for every prompt the bot uses, the domain whose
text is actually in effect (the same lookup the bot runs, chat.prompts.resolve_prompt). Read-only, for the UI.
"""

from __future__ import annotations

from typing import Any

from chat.prompts import parent_chain, resolve_prompt
from core.config import DEFAULT_DOMAIN

#: The prompts the bot uses, as (agent type, prompt type).
USED_PROMPTS: tuple[tuple[str, str], ...] = (
    ("sales", "base-prompt"),
    ("sales", "company"),
    ("sales", "intro-message"),
    ("sales", "fetch-contact-info"),
    ("generic", "system"),
    ("generic", "fetch-name"),
)
PREVIEW_CHARS = 200


def _origin(key: str, source: str | None) -> tuple[str, str]:
    """(code, label) for where an effective prompt comes from."""
    if source is None:
        return "missing", "not set anywhere in the chain"
    if source == key:
        return "own", "own"
    if source == DEFAULT_DOMAIN:
        return "default", f"default ({DEFAULT_DOMAIN})"
    return "inherited", f"inherited from {source}"


def describe(key: str) -> dict[str, Any]:
    """
    {"key", "chain": [keys, nearest first], "ends_at_default": bool,
     "prompts": [{agent_type, type, source, origin, label, preview}]}
    where origin is "own", "inherited", "default" (the text comes from COMMON) or "missing".
    """
    chain = parent_chain(key)
    prompts = []
    for agent_type, prompt_type in USED_PROMPTS:
        text, source = resolve_prompt(key, agent_type, prompt_type)
        origin, label = _origin(key, source)
        preview = (text or "").strip()
        if len(preview) > PREVIEW_CHARS:
            preview = preview[: PREVIEW_CHARS - 1].rstrip() + "…"
        prompts.append(
            {
                "agent_type": agent_type,
                "type": prompt_type,
                "source": source,
                "origin": origin,
                "label": label,
                "preview": preview,
            }
        )
    return {"key": key, "chain": chain, "ends_at_default": chain[-1] == DEFAULT_DOMAIN, "prompts": prompts}
