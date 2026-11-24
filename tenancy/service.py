"""Tenancy rules: the trial cap that keeps a not-yet-enabled tenant's widget from running up LLM calls."""

from tenancy import repository

TRIAL_LIMIT_REPLY = "This assistant isn't active yet."


def conversation_allowed(domain_key: str, session_id: str) -> bool:
    """May this chat message be answered by the LLM?

    True when the tenant is enabled, when the session already has a chat_info row (a started conversation
    is finished), or when the tenant has fewer than its trial limit of distinct sessions on its domains.
    A domain no tenant owns is allowed: the cap only ever applies to tenants that exist.
    """
    status = repository.trial_status(domain_key, session_id)
    if status is None or status["enabled"] or status["has_session"]:
        return True
    return status["used"] < status["limit"]
