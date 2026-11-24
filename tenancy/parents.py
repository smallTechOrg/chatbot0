"""Setting a website's parent: the rules shared by the tenant API (/api/domains) and the admin API (/api/admin)."""

from __future__ import annotations

from typing import Any

from chat.prompt_chain import describe
from chat.prompts import MAX_CHAIN, find_parent_key
from core.config import DEFAULT_DOMAIN
from core.errors import ServiceError
from tenancy import repository


class ParentError(ServiceError):
    """A parent change the API answers with `status` and a message that is safe to show."""


def _would_loop(key: str, parent_key: str) -> bool:
    """True when `key` is on the way up from the proposed parent (the walk is capped, like the lookup)."""
    current: str | None = parent_key
    for _ in range(MAX_CHAIN * 10):
        if current is None:
            return False
        if current == key:
            return True
        current = find_parent_key(current)
    return True  # an endless chain above the proposed parent is not something to build on


def set_parent(key: str, parent_key: Any, *, same_tenant_only: bool) -> dict[str, Any]:
    """
    Make `parent_key` the parent of the website `key` and return its new prompt chain.

    Every row with the key (the main row and the www alias) changes together, because the prompt lookup finds a
    parent by key. With same_tenant_only the parent must be COMMON or a website of the same tenant as `key`:
    a company prompt is never inherited from another tenant's website. Self-parenting and loops are a 400.
    """
    if not isinstance(parent_key, str) or not parent_key.strip():
        raise ParentError("Choose the parent website.", 400)
    parent_key = parent_key.strip()
    if not repository.domain_key_exists(key):
        raise ParentError("No such website.", 404)
    if parent_key == key:
        raise ParentError("A website cannot be its own parent.", 400)
    parent_id = repository.parent_row_id(parent_key)
    if parent_id is None:
        raise ParentError("The parent website does not exist.", 400)
    if same_tenant_only and parent_key != DEFAULT_DOMAIN:
        owner = repository.domain_key_tenant(key)
        if owner is None or repository.domain_key_tenant(parent_key) != owner:
            raise ParentError("The parent must be one of your own websites, or the default (COMMON).", 400)
    if _would_loop(key, parent_key):
        raise ParentError(
            f"{parent_key} is below {key} in the hierarchy, so it cannot be its parent (that is a loop).", 400
        )
    repository.set_key_parent(key, parent_id)
    return describe(key)
