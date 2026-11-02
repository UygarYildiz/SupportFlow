from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.agent_run_step import AgentRunStep
from app.db.types import TZDateTime, str_enum, utcnow
from app.domain.enums import AgentRunStatus


class AgentRun(Base):
    """One analysis attempt for a ticket (ADR-005). Business state, not a graph checkpoint."""

    __tablename__ = "agent_runs"
    __table_args__ = (
        # At most one queued/running run per ticket, guaranteed by the database.
        Index(
            "uq_agent_runs_one_active_per_ticket",
            "ticket_id",
            unique=True,
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    requested_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[AgentRunStatus] = mapped_column(
        str_enum(AgentRunStatus, "agent_run_status"), default=AgentRunStatus.QUEUED
    )
    model: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    # Validated AnalysisResult (JSON). Raw model output is never stored.
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(String(500))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime)

    steps: Mapped[list[AgentRunStep]] = relationship(order_by=AgentRunStep.sequence)
