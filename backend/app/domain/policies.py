"""NovaShop policy rules v1 (docs/REQUIREMENTS.md section 4).

These deterministic rules are the source of truth for decisions. The agent
and, later, policy documents (RAG) may explain them but never override them.
All functions are pure: the caller supplies the current time.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from app.domain.enums import OrderStatus

POLICY_VERSION = "v1"

RETURN_WINDOW_DAYS = 14
DAMAGE_REPORT_WINDOW_DAYS = 30
DELIVERY_DELAY_BUSINESS_DAYS = 7
ADDRESS_CHANGEABLE_STATUSES = frozenset({OrderStatus.PENDING, OrderStatus.PROCESSING})


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    rule: str
    reason: str


def check_address_change(order_status: OrderStatus) -> PolicyDecision:
    allowed = order_status in ADDRESS_CHANGEABLE_STATUSES
    reason = (
        "Order has not shipped yet; the shipping address can be changed."
        if allowed
        else f"Order is '{order_status.value}'; the address can only change before shipping."
    )
    return PolicyDecision(allowed, f"address_change_{POLICY_VERSION}", reason)


def check_return_request(delivered_at: datetime | None, now: datetime) -> PolicyDecision:
    return _within_window_after_delivery(
        delivered_at, now, RETURN_WINDOW_DAYS, f"returns_{POLICY_VERSION}", "Return"
    )


def check_damage_report(delivered_at: datetime | None, now: datetime) -> PolicyDecision:
    return _within_window_after_delivery(
        delivered_at, now, DAMAGE_REPORT_WINDOW_DAYS, f"damaged_goods_{POLICY_VERSION}", "Damage"
    )


def is_delivery_delayed(
    order_status: OrderStatus, shipped_at: datetime | None, now: datetime
) -> bool:
    """A shipped order not delivered within 7 business days of shipping is delayed."""
    if order_status != OrderStatus.SHIPPED or shipped_at is None:
        return False
    return business_days_between(shipped_at.date(), now.date()) > DELIVERY_DELAY_BUSINESS_DAYS


def business_days_between(start: date, end: date) -> int:
    """Number of weekdays after `start` up to and including `end`."""
    days = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if current.weekday() < 5:
            days += 1
    return days


def _within_window_after_delivery(
    delivered_at: datetime | None, now: datetime, window_days: int, rule: str, label: str
) -> PolicyDecision:
    if delivered_at is None:
        return PolicyDecision(False, rule, "Order has not been delivered yet.")
    deadline = delivered_at + timedelta(days=window_days)
    if now <= deadline:
        return PolicyDecision(
            True, rule, f"{label} requested within {window_days} days of delivery."
        )
    return PolicyDecision(
        False, rule, f"{label} window of {window_days} days after delivery has passed."
    )
