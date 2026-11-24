"""
Plans and their monthly conversation caps. The numbers are the ones on the pricing page
(frontend/src/content/plans.ts; a test keeps the two in step). A conversation is one chat session, counted in the
calendar month (Asia/Kolkata) in which the visitor first wrote.
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_PLAN = "free"
UNLIMITED_PLAN = "pro"
PLAN_TIMEZONE = "Asia/Kolkata"

#: plan key -> conversations per month; None means unlimited.
PLAN_LIMITS: dict[str, int | None] = {"free": 200, "basic": 1000, "pro": None}
PLAN_NAMES = {"free": "Free", "basic": "Basic", "pro": "Pro"}

#: What a visitor sees when the tenant's plan is used up for the month. No LLM call is made.
PLAN_LIMIT_REPLY = (
    "This assistant has reached its conversation limit for this month. "
    "Please try again next month, or contact the business directly."
)


def monthly_limit(plan: str) -> int | None:
    """The plan's cap, or None when unlimited. An unknown plan name is treated as the default plan."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[DEFAULT_PLAN])


def capped_plans() -> list[str]:
    return [key for key, limit in PLAN_LIMITS.items() if limit is not None]


def month_start(now: datetime | None = None) -> datetime:
    """Midnight on the first of the current month in PLAN_TIMEZONE (an aware datetime)."""
    local = (now or datetime.now(ZoneInfo(PLAN_TIMEZONE))).astimezone(ZoneInfo(PLAN_TIMEZONE))
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
