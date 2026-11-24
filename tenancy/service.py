"""Tenancy rules: the trial cap for tenants not yet enabled, and the monthly plan cap for enabled ones."""

from tenancy import plans, repository

TRIAL_LIMIT_REPLY = "This assistant isn't active yet."
PLAN_LIMIT_REPLY = plans.PLAN_LIMIT_REPLY


def block_reply(domain_key: str, session_id: str) -> str | None:
    """
    None when this chat message may be answered by the LLM; otherwise the fixed reply to give instead (no LLM call).

    - A tenant that is not enabled has a trial: its first `trial_conversation_limit` sessions are answered.
    - An enabled tenant has a monthly cap from its plan, counted in distinct sessions that started this calendar
      month (Asia/Kolkata) across its domains. The unlimited plan has none.
    - A session that already has a chat_info row is always finished: a started conversation is not cut off.
    - A domain no tenant owns is allowed: the caps only ever apply to tenants that exist.
    """
    status = repository.trial_status(domain_key, session_id, plans.month_start(), plans.capped_plans())
    if status is None or status["has_session"]:
        return None
    if not status["enabled"]:
        return None if status["used"] < status["limit"] else TRIAL_LIMIT_REPLY
    cap = plans.monthly_limit(status["plan"])
    if cap is None or status["month_used"] < cap:
        return None
    return PLAN_LIMIT_REPLY


def conversation_allowed(domain_key: str, session_id: str) -> bool:
    """May this chat message be answered by the LLM? (block_reply is None.)"""
    return block_reply(domain_key, session_id) is None
