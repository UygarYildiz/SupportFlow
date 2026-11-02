from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import DbSession, StaffUser
from app.db.models import Ticket
from app.domain.enums import TicketCategory, TicketPriority, TicketStatus
from app.schemas.commerce import CustomerSummary, OrderOut
from app.schemas.common import ErrorResponse, Page
from app.schemas.tickets import TicketCreate, TicketDetail, TicketEventOut, TicketOut, TicketUpdate
from app.services.tickets import TicketFilters, TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _detail(service: TicketService, ticket: Ticket) -> TicketDetail:
    order = service.get_order(ticket)
    return TicketDetail(
        **TicketOut.model_validate(ticket).model_dump(),
        message=ticket.message,
        customer=CustomerSummary.model_validate(service.get_customer(ticket)),
        order=OrderOut.model_validate(order) if order else None,
        events=[TicketEventOut.model_validate(event) for event in ticket.events],
    )


@router.get("")
def list_tickets(
    _: StaffUser,
    session: DbSession,
    status_filter: Annotated[TicketStatus | None, Query(alias="status")] = None,
    priority: TicketPriority | None = None,
    customer_id: str | None = None,
    category: TicketCategory | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[TicketOut]:
    filters = TicketFilters(
        status=status_filter, priority=priority, customer_id=customer_id, category=category
    )
    tickets, total = TicketService(session).list(filters, limit=limit, offset=offset)
    return Page(
        items=[TicketOut.model_validate(ticket) for ticket in tickets],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse}},
)
def create_ticket(body: TicketCreate, user: StaffUser, session: DbSession) -> TicketDetail:
    service = TicketService(session)
    ticket = service.create(
        customer_id=body.customer_id,
        order_id=body.order_id,
        subject=body.subject,
        message=body.message,
        priority=body.priority,
        actor=user,
    )
    return _detail(service, ticket)


@router.get("/{ticket_id}", responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}})
def get_ticket(ticket_id: int, _: StaffUser, session: DbSession) -> TicketDetail:
    service = TicketService(session)
    return _detail(service, service.get(ticket_id))


@router.patch(
    "/{ticket_id}",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    },
)
def update_ticket(
    ticket_id: int, body: TicketUpdate, user: StaffUser, session: DbSession
) -> TicketDetail:
    service = TicketService(session)
    ticket = service.update(ticket_id, status=body.status, priority=body.priority, actor=user)
    return _detail(service, ticket)
