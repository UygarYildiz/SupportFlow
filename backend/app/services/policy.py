from collections.abc import Callable
from datetime import UTC, datetime

from app.domain import policies
from app.domain.policies import PolicyDecision
from app.services.orders import OrderService


def _utcnow() -> datetime:
    return datetime.now(UTC)


class PolicyService:
    """Applies the deterministic NovaShop rules to a customer's order.

    Lookups are scoped to the customer, so a policy check can never reveal
    another customer's order. The clock is injectable for tests.
    """

    def __init__(self, orders: OrderService, clock: Callable[[], datetime] = _utcnow) -> None:
        self.orders = orders
        self.clock = clock

    def address_change(self, customer_id: str, order_id: str) -> PolicyDecision:
        order = self.orders.get_customer_order(customer_id, order_id)
        return policies.check_address_change(order.status)

    def return_request(self, customer_id: str, order_id: str) -> PolicyDecision:
        order = self.orders.get_customer_order(customer_id, order_id)
        return policies.check_return_request(order.delivered_at, self.clock())

    def damage_report(self, customer_id: str, order_id: str) -> PolicyDecision:
        order = self.orders.get_customer_order(customer_id, order_id)
        return policies.check_damage_report(order.delivered_at, self.clock())

    def delivery(self, customer_id: str, order_id: str) -> PolicyDecision:
        order = self.orders.get_customer_order(customer_id, order_id)
        return policies.check_delivery(order.status, order.shipped_at, self.clock())

    def is_delivery_delayed(self, customer_id: str, order_id: str) -> bool:
        order = self.orders.get_customer_order(customer_id, order_id)
        return policies.is_delivery_delayed(order.status, order.shipped_at, self.clock())
