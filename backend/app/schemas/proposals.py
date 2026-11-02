from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.domain.enums import ActionType, ActorType, Decision, ProposalStatus
from app.schemas.common import ApiModel


class ProposalOut(ApiModel):
    id: int
    ticket_id: int
    run_id: int
    order_id: str
    type: ActionType
    payload: dict[str, Any]
    reason: str
    policy_rule: str
    status: ProposalStatus
    version: int = Field(description="Send as expected_version when deciding")
    created_at: datetime
    expires_at: datetime
    decided_by: int | None
    decided_at: datetime | None
    decision_note: str | None
    executed_at: datetime | None
    failure_reason: str | None
    can_decide: bool = Field(
        default=False, description="Whether the current user's role may decide this type"
    )


class DecisionRequest(BaseModel):
    decision: Decision
    expected_version: int = Field(ge=1)
    note: str | None = Field(default=None, max_length=500)


class AuditLogOut(ApiModel):
    id: int
    actor_type: ActorType
    actor_id: int | None
    action: str
    resource_type: str
    resource_id: str
    ticket_id: int | None
    details: dict[str, Any]
    occurred_at: datetime
