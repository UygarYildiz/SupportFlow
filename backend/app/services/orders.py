from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Customer, Order
from app.domain.errors import NotFoundError


class OrderService:
    """Read access to the mock CRM / order system."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_customer(self, customer_id: str) -> Customer:
        customer = self.session.get(Customer, customer_id)
        if customer is None:
            raise NotFoundError("Customer", customer_id)
        return customer

    def get_order(self, order_id: str) -> Order:
        order = self.session.get(Order, order_id)
        if order is None:
            raise NotFoundError("Order", order_id)
        return order

    def get_customer_order(self, customer_id: str, order_id: str) -> Order:
        """Order lookup scoped to one customer.

        Another customer's order is reported exactly like a missing one, so the
        caller learns nothing about orders outside the scope. The agent's tools
        (Phase 4) use this method, never `get_order`.
        """
        order = self.session.scalar(
            select(Order).where(Order.id == order_id, Order.customer_id == customer_id)
        )
        if order is None:
            raise NotFoundError("Order", order_id)
        return order

    def list_customer_orders(self, customer_id: str) -> list[Order]:
        self.get_customer(customer_id)
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.created_at.desc(), Order.id)
        )
        return list(self.session.scalars(stmt))
