from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZDateTime, str_enum, utcnow
from app.domain.enums import ActionType, ActorType, ExecutionOutcome, ProposalStatus


class ActionProposal(Base):
    """A state-changing action suggested by an analysis run. Never executed without approval."""

    __tablename__ = "action_proposals"
    __table_args__ = (
        # The proposal's order must belong to the ticket's customer.
        ForeignKeyConstraint(
            ["order_id", "customer_id"],
            ["orders.id", "orders.customer_id"],
            name="fk_action_proposals_order_id_customer_id_orders",
        ),
        # At most one open proposal per ticket.
        Index(
            "uq_action_proposals_one_open_per_ticket",
            "ticket_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'approved', 'executing')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("agent_runs.id"), unique=True)
    customer_id: Mapped[str] = mapped_column(String(32))
    order_id: Mapped[str] = mapped_column(String(32))
    type: Mapped[ActionType] = mapped_column(str_enum(ActionType, "action_type"))
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    payload_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(Text)
    policy_rule: Mapped[str] = mapped_column(String(64))
    status: Mapped[ProposalStatus] = mapped_column(
        str_enum(ProposalStatus, "proposal_status"), default=ProposalStatus.PENDING
    )
    # Optimistic locking: a decision must name the version it was based on.
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(TZDateTime)
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    decision_note: Mapped[str | None] = mapped_column(String(500))
    executed_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    failure_reason: Mapped[str | None] = mapped_column(String(500))


class ActionExecution(Base):
    """The one and only execution attempt result of a proposal."""

    __tablename__ = "action_executions"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("action_proposals.id"), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    outcome: Mapped[ExecutionOutcome] = mapped_column(
        str_enum(ExecutionOutcome, "execution_outcome")
    )
    external_ref: Mapped[str | None] = mapped_column(String(64))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    executed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


class RefundRequest(Base):
    """Mock finance record. Creating one moves no money."""

    __tablename__ = "refund_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("action_proposals.id"), unique=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3))
    reason: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="open")
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)


class AuditLog(Base):
    """Append-only trail. UPDATE and DELETE are blocked by a database trigger."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_type: Mapped[ActorType] = mapped_column(str_enum(ActorType, "audit_actor_type"))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(64))
    resource_type: Mapped[str] = mapped_column(String(32))
    resource_id: Mapped[str] = mapped_column(String(64))
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), index=True)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # PII redacted
    occurred_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
