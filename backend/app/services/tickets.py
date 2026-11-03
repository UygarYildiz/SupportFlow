from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models import ActionProposal, Customer, Order, Ticket, TicketEvent, User
from app.domain.enums import (
    ActorType,
    ProposalStatus,
    TicketCategory,
    TicketEventType,
    TicketPriority,
    TicketStatus,
)
from app.domain.errors import BusinessRuleViolationError, NotFoundError
from app.domain.ticket_status import ensure_manual_transition


@dataclass(frozen=True)
class TicketFilters:
    status: TicketStatus | None = None
    priority: TicketPriority | None = None
    customer_id: str | None = None
    category: TicketCategory | None = None


class TicketService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        filters: TicketFilters,
        limit: int,
        offset: int,
        *,
        recently_updated: bool = False,
    ) -> tuple[list[Ticket], int]:
        """Newest first by creation time, or by last update when `recently_updated`."""
        conditions = []
        if filters.status is not None:
            conditions.append(Ticket.status == filters.status)
        if filters.priority is not None:
            conditions.append(Ticket.priority == filters.priority)
        if filters.customer_id is not None:
            conditions.append(Ticket.customer_id == filters.customer_id)
        if filters.category is not None:
            conditions.append(Ticket.category == filters.category)

        total = self.session.scalar(select(func.count(Ticket.id)).where(*conditions)) or 0
        stmt = (
            select(Ticket)
            .where(*conditions)
            .options(selectinload(Ticket.customer))
            .order_by(
                (Ticket.updated_at if recently_updated else Ticket.created_at).desc(),
                Ticket.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt)), total

    def summary(self) -> tuple[dict[TicketStatus, int], int]:
        """(tickets per status, pending proposals). Every status is present, zero included."""
        rows = self.session.execute(select(Ticket.status, func.count()).group_by(Ticket.status))
        counts = dict.fromkeys(TicketStatus, 0) | {status: count for status, count in rows}
        pending = self.session.scalar(
            select(func.count(ActionProposal.id)).where(
                ActionProposal.status == ProposalStatus.PENDING
            )
        )
        return counts, pending or 0

    def get(self, ticket_id: int) -> Ticket:
        stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.events))
            # Refresh objects already in the session so new events are included.
            .execution_options(populate_existing=True)
        )
        ticket = self.session.scalar(stmt)
        if ticket is None:
            raise NotFoundError("Ticket", ticket_id)
        return ticket

    def get_customer(self, ticket: Ticket) -> Customer:
        customer = self.session.get(Customer, ticket.customer_id)
        if customer is None:  # pragma: no cover - prevented by the foreign key
            raise NotFoundError("Customer", ticket.customer_id)
        return customer

    def get_order(self, ticket: Ticket) -> Order | None:
        return self.session.get(Order, ticket.order_id) if ticket.order_id else None

    def create(
        self,
        *,
        customer_id: str,
        order_id: str | None,
        subject: str,
        message: str,
        priority: TicketPriority,
        actor: User,
    ) -> Ticket:
        if self.session.get(Customer, customer_id) is None:
            raise BusinessRuleViolationError(f"Bilinmeyen müşteri: '{customer_id}'")
        if order_id is not None:
            owned = self.session.scalar(
                select(Order.id).where(Order.id == order_id, Order.customer_id == customer_id)
            )
            if owned is None:
                # Same message whether the order is missing or belongs to someone else.
                raise BusinessRuleViolationError(
                    f"'{order_id}' bu müşterinin hiçbir siparişiyle eşleşmiyor"
                )

        ticket = Ticket(
            customer_id=customer_id,
            order_id=order_id,
            subject=subject,
            message=message,
            priority=priority,
            status=TicketStatus.NEW,
        )
        self.session.add(ticket)
        self.session.flush()
        self._record(ticket, TicketEventType.CREATED, actor, {"priority": priority.value})
        self.session.commit()
        return self.get(ticket.id)

    def update(
        self,
        ticket_id: int,
        *,
        status: TicketStatus | None,
        priority: TicketPriority | None,
        actor: User,
    ) -> Ticket:
        # Row lock: two concurrent updates cannot both pass the transition check.
        ticket = self.session.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
        if ticket is None:
            raise NotFoundError("Ticket", ticket_id)

        if status is not None and status != ticket.status:
            ensure_manual_transition(ticket.status, status)
            self._record(
                ticket,
                TicketEventType.STATUS_CHANGED,
                actor,
                {"from": ticket.status.value, "to": status.value},
            )
            ticket.status = status

        if priority is not None and priority != ticket.priority:
            self._record(
                ticket,
                TicketEventType.PRIORITY_CHANGED,
                actor,
                {"from": ticket.priority.value, "to": priority.value},
            )
            ticket.priority = priority

        self.session.commit()
        return self.get(ticket_id)

    def _record(
        self, ticket: Ticket, event_type: TicketEventType, actor: User, payload: dict[str, Any]
    ) -> None:
        self.session.add(
            TicketEvent(
                ticket_id=ticket.id,
                event_type=event_type,
                actor_type=ActorType.USER,
                actor_id=actor.id,
                payload=payload,
            )
        )
