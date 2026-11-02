from datetime import UTC, date, datetime, timedelta

import pytest

from app.domain.enums import OrderStatus
from app.domain.policies import (
    business_days_between,
    check_address_change,
    check_damage_report,
    check_return_request,
    is_delivery_delayed,
)

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)  # a Monday


@pytest.mark.parametrize(
    ("status", "allowed"),
    [
        (OrderStatus.PENDING, True),
        (OrderStatus.PROCESSING, True),
        (OrderStatus.SHIPPED, False),
        (OrderStatus.DELIVERED, False),
        (OrderStatus.CANCELLED, False),
    ],
)
def test_address_can_only_change_before_shipping(status: OrderStatus, allowed: bool) -> None:
    decision = check_address_change(status)
    assert decision.allowed is allowed
    assert decision.rule == "address_change_v1"


@pytest.mark.parametrize(
    ("days_since_delivery", "allowed"),
    [(0, True), (13, True), (14, True), (15, False), (60, False)],
)
def test_return_window_is_14_days_after_delivery(days_since_delivery: int, allowed: bool) -> None:
    delivered_at = NOW - timedelta(days=days_since_delivery)
    assert check_return_request(delivered_at, NOW).allowed is allowed


@pytest.mark.parametrize(("days_since_delivery", "allowed"), [(30, True), (31, False)])
def test_damage_can_be_reported_within_30_days(days_since_delivery: int, allowed: bool) -> None:
    delivered_at = NOW - timedelta(days=days_since_delivery)
    assert check_damage_report(delivered_at, NOW).allowed is allowed


def test_return_is_not_possible_before_delivery() -> None:
    decision = check_return_request(None, NOW)
    assert not decision.allowed
    assert "not been delivered" in decision.reason


def test_business_days_skip_weekends() -> None:
    friday, next_monday = date(2026, 10, 30), date(2026, 11, 2)
    assert business_days_between(friday, next_monday) == 1
    assert business_days_between(next_monday, next_monday) == 0


def test_shipped_order_is_delayed_after_seven_business_days() -> None:
    thursday = datetime(2026, 10, 22, tzinfo=UTC)  # 7 business days before NOW
    wednesday = datetime(2026, 10, 21, tzinfo=UTC)  # 8 business days before NOW
    assert not is_delivery_delayed(OrderStatus.SHIPPED, thursday, NOW)
    assert is_delivery_delayed(OrderStatus.SHIPPED, wednesday, NOW)
    # Only orders in transit can be delayed.
    assert not is_delivery_delayed(OrderStatus.DELIVERED, NOW - timedelta(days=30), NOW)
