"""Import every model module here so Alembic autogenerate sees all tables."""

from app.db.models.commerce import Customer, Order
from app.db.models.ticket import Ticket, TicketEvent
from app.db.models.user import User

__all__ = ["Customer", "Order", "Ticket", "TicketEvent", "User"]
