"""Read-only lookups on behalf of one ticket (Phase 8, ADR-015).

The ticket decides whose data may be read: the customer is always taken from the
ticket row in the database, never from the caller. Another customer's order is
reported exactly like a missing one. Used by the MCP adapter (`app/mcp/`); the
REST API exposes the same data through `/tickets`, `/orders` and `/customers`.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Order, Ticket
from app.domain.errors import NotFoundError
from app.services.orders import OrderService


class SupportLookupService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ticket(self, ticket_id: int) -> Ticket:
        ticket = self.session.get(Ticket, ticket_id)
        if ticket is None:
            raise NotFoundError("Ticket", ticket_id)
        return ticket

    def order_for_ticket(self, ticket_id: int, order_id: str) -> Order:
        customer_id = self.ticket(ticket_id).customer_id
        return OrderService(self.session).get_customer_order(customer_id, order_id)

    def orders_for_ticket(self, ticket_id: int, limit: int) -> list[Order]:
        customer_id = self.ticket(ticket_id).customer_id
        return OrderService(self.session).list_customer_orders(customer_id)[:limit]

    def ticket_history(self, ticket_id: int, limit: int) -> list[Ticket]:
        """The customer's other tickets, newest first (the ticket itself is excluded)."""
        ticket = self.ticket(ticket_id)
        stmt = (
            select(Ticket)
            .where(Ticket.customer_id == ticket.customer_id, Ticket.id != ticket.id)
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))
