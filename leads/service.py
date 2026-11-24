"""Who may see and change which lead: a user only reaches the leads of their own tenant; admins reach all."""

from __future__ import annotations

from typing import Any

from chat.history import read_history
from core.config import status_type
from core.errors import ServiceError
from leads import repository

MAX_REMARKS = 5000
STATUSES = frozenset(s.value for s in status_type)


class LeadError(ServiceError):
    """A leads request the API answers with `status` and a message that is safe to show."""


def list_leads(user: dict[str, Any], tenant_id: int | None = None) -> list[dict[str, Any]]:
    """A user gets their tenant's leads. An admin gets every lead, or one tenant's with `tenant_id`."""
    if user["is_admin"]:
        return repository.list_leads(tenant_id)
    if tenant_id is not None and tenant_id != user["tenant_id"]:
        raise LeadError("You can only see your own leads.", 403)
    return repository.list_leads(user["tenant_id"])


def _authorize(user: dict[str, Any], session_id: str) -> None:
    owner = repository.find_lead_owner(session_id)
    if owner is None:
        raise LeadError("No such lead.", 404)
    if not user["is_admin"] and owner["tenant_id"] != user["tenant_id"]:
        raise LeadError("This lead belongs to another account.", 403)


def history(user: dict[str, Any], session_id: str) -> list[dict[str, str]]:
    _authorize(user, session_id)
    return read_history(session_id)


def update_lead(user: dict[str, Any], session_id: str, data: dict[str, Any]) -> None:
    """Change status, remarks and/or is_active of a lead the user may touch."""
    status, remarks, is_active = data.get("status"), data.get("remarks"), data.get("is_active")
    if status is None and remarks is None and is_active is None:
        raise LeadError("Send status, remarks or is_active.", 400)
    if status is not None and status not in STATUSES:
        raise LeadError(f"Status must be one of {', '.join(sorted(STATUSES))}.", 400)
    if remarks is not None and (not isinstance(remarks, str) or len(remarks) > MAX_REMARKS):
        raise LeadError(f"Remarks must be text of at most {MAX_REMARKS} characters.", 400)
    if is_active is not None and not isinstance(is_active, bool):
        raise LeadError("is_active must be true or false.", 400)
    _authorize(user, session_id)
    repository.update_chat_info(session_id, status, remarks, is_active)
