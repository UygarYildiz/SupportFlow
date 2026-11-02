from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, ForeignKeyConstraint, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.commerce import Customer
from app.db.types import TZDateTime, str_enum, utcnow
from app.domain.enums import (
    ActorType,
    TicketCategory,
    TicketEventType,
    TicketPriority,
    TicketStatus,
)


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status_created_at", "status", "created_at"),
        # order_id must reference an order of the same customer (NULL allowed).
        ForeignKeyConstraint(
            ["order_id", "customer_id"],
            ["orders.id", "orders.customer_id"],
            name="fk_tickets_order_id_customer_id_orders",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    # Optional: the order the customer referred to, if it belongs to them.
    order_id: Mapped[str | None] = mapped_column(String(32))
    subject: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[TicketStatus] = mapped_column(
        str_enum(TicketStatus, "ticket_status"), default=TicketStatus.NEW
    )
    priority: Mapped[TicketPriority] = mapped_column(
        str_enum(TicketPriority, "ticket_priority"), default=TicketPriority.MEDIUM
    )
    # Set by a successful analysis; NULL until the ticket has been analyzed.
    category: Mapped[TicketCategory | None] = mapped_column(
        str_enum(TicketCategory, "ticket_category")
    )
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow, onupdate=utcnow)

    events: Mapped[list["TicketEvent"]] = relationship(
        back_populates="ticket", order_by="TicketEvent.id"
    )
    # Loaded on demand (never joined: ticket rows are locked with SELECT ... FOR UPDATE).
    customer: Mapped["Customer"] = relationship()

    @property
    def customer_name(self) -> str:
        return self.customer.display_name


class TicketEvent(Base):
    """Append-only history of a ticket."""

    __tablename__ = "ticket_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    event_type: Mapped[TicketEventType] = mapped_column(
        str_enum(TicketEventType, "ticket_event_type")
    )
    actor_type: Mapped[ActorType] = mapped_column(str_enum(ActorType, "actor_type"))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)

    ticket: Mapped[Ticket] = relationship(back_populates="events")
