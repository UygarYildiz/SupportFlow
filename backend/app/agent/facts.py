"""Collects the facts the model may see, always scoped to the ticket's customer."""

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.agent.schemas import OrderFact, TicketFacts, order_fact_total
from app.db.models import Order, Ticket
from app.domain.errors import NotFoundError
from app.services.orders import OrderService

MAX_ORDERS_IN_CONTEXT = 10
ORDER_ID_PATTERN = re.compile(r"\bORD-\d{3,6}\b", re.IGNORECASE)


def gather_facts(session: Session, ticket: Ticket, now: datetime) -> TicketFacts:
    orders = OrderService(session)
    customer = orders.get_customer(ticket.customer_id)
    customer_orders = orders.list_customer_orders(ticket.customer_id)[:MAX_ORDERS_IN_CONTEXT]
    in_context = {order.id for order in customer_orders}

    mentioned = {match.upper() for match in ORDER_ID_PATTERN.findall(ticket.message)}
    unknown: list[str] = []
    for order_id in sorted(mentioned - in_context):
        try:
            # Older order of the same customer: add it. Another customer's: unknown.
            customer_orders.append(orders.get_customer_order(ticket.customer_id, order_id))
        except NotFoundError:
            unknown.append(order_id)

    return TicketFacts(
        ticket_id=ticket.id,
        subject=ticket.subject,
        message=ticket.message,
        customer_name=customer.display_name,
        linked_order_id=ticket.order_id,
        orders=[_order_fact(order) for order in customer_orders],
        unknown_order_ids=unknown,
        reference_time=now,
    )


def _order_fact(order: Order) -> OrderFact:
    return OrderFact(
        id=order.id,
        status=order.status,
        items=[f"{item['quantity']} x {item['name']}" for item in order.items],
        total=order_fact_total(order.total_amount, order.currency),
        shipping_address=order.shipping_address,
        created_at=order.created_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
    )
