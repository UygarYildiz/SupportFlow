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

# Reasons end up in customer-facing drafts, so statuses are written as words.
ORDER_STATUS_LABEL = {
    OrderStatus.PENDING: "beklemede",
    OrderStatus.PROCESSING: "hazırlanıyor",
    OrderStatus.SHIPPED: "kargoda",
    OrderStatus.DELIVERED: "teslim edildi",
    OrderStatus.CANCELLED: "iptal edildi",
}


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    rule: str
    reason: str


def check_address_change(order_status: OrderStatus) -> PolicyDecision:
    allowed = order_status in ADDRESS_CHANGEABLE_STATUSES
    reason = (
        "Sipariş henüz kargoya verilmedi; teslimat adresi değiştirilebilir."
        if allowed
        else f"Sipariş durumu: {ORDER_STATUS_LABEL[order_status]}. Adres yalnızca sipariş kargoya "
        "verilmeden önce değiştirilebilir."
    )
    return PolicyDecision(allowed, f"address_change_{POLICY_VERSION}", reason)


def check_return_request(delivered_at: datetime | None, now: datetime) -> PolicyDecision:
    return _within_window_after_delivery(
        delivered_at, now, RETURN_WINDOW_DAYS, f"returns_{POLICY_VERSION}", "İade talebi", "iade"
    )


def check_damage_report(delivered_at: datetime | None, now: datetime) -> PolicyDecision:
    return _within_window_after_delivery(
        delivered_at,
        now,
        DAMAGE_REPORT_WINDOW_DAYS,
        f"damaged_goods_{POLICY_VERSION}",
        "Hasar bildirimi",
        "hasar bildirimi",
    )


def is_delivery_delayed(
    order_status: OrderStatus, shipped_at: datetime | None, now: datetime
) -> bool:
    """A shipped order not delivered within 7 business days of shipping is delayed."""
    if order_status != OrderStatus.SHIPPED or shipped_at is None:
        return False
    return business_days_between(shipped_at.date(), now.date()) > DELIVERY_DELAY_BUSINESS_DAYS


def check_delivery(
    order_status: OrderStatus, shipped_at: datetime | None, now: datetime
) -> PolicyDecision:
    """Informational: `allowed` is True when the order counts as delayed."""
    rule = f"delivery_{POLICY_VERSION}"
    if order_status != OrderStatus.SHIPPED or shipped_at is None:
        return PolicyDecision(
            False, rule, f"Sipariş durumu: {ORDER_STATUS_LABEL[order_status]}. Şu anda yolda değil."
        )
    days = business_days_between(shipped_at.date(), now.date())
    delayed = days > DELIVERY_DELAY_BUSINESS_DAYS
    reason = f"Sipariş {days} iş günü önce kargoya verildi; standart teslimat 3-5 iş günü sürer" + (
        f" ve {DELIVERY_DELAY_BUSINESS_DAYS} iş gününden sonra gecikmiş sayılır."
        if delayed
        else "."
    )
    return PolicyDecision(delayed, rule, reason)


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
    delivered_at: datetime | None,
    now: datetime,
    window_days: int,
    rule: str,
    label: str,
    noun: str,
) -> PolicyDecision:
    if delivered_at is None:
        return PolicyDecision(False, rule, "Sipariş henüz teslim edilmedi.")
    deadline = delivered_at + timedelta(days=window_days)
    if now <= deadline:
        return PolicyDecision(
            True, rule, f"{label} teslimattan sonraki {window_days} gün içinde yapıldı."
        )
    return PolicyDecision(
        False, rule, f"Teslimattan sonraki {window_days} günlük {noun} süresi doldu."
    )
