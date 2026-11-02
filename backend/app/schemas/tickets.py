from datetime import datetime
from typing import Any, Self

from pydantic import BaseModel, Field, model_validator

from app.domain.enums import ActorType, TicketEventType, TicketPriority, TicketStatus
from app.schemas.commerce import CustomerSummary, OrderOut
from app.schemas.common import ApiModel


class TicketCreate(BaseModel):
    customer_id: str = Field(min_length=1, max_length=32)
    order_id: str | None = Field(default=None, min_length=1, max_length=32)
    subject: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    """Only status and priority are editable; customer-written content is immutable."""

    status: TicketStatus | None = None
    priority: TicketPriority | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self) -> Self:
        if self.status is None and self.priority is None:
            raise ValueError("Provide at least one of: status, priority")
        return self


class TicketOut(ApiModel):
    id: int
    customer_id: str
    order_id: str | None
    subject: str
    status: TicketStatus
    priority: TicketPriority
    created_at: datetime
    updated_at: datetime


class TicketEventOut(ApiModel):
    id: int
    event_type: TicketEventType
    actor_type: ActorType
    actor_id: int | None
    payload: dict[str, Any]
    occurred_at: datetime


class TicketDetail(TicketOut):
    message: str
    customer: CustomerSummary
    order: OrderOut | None
    events: list[TicketEventOut]
