"""Lifecycle of analysis runs (ADR-005).

This service owns the business state: run status, ticket status, history.
It knows nothing about LLMs; the agent hands it a validated result.
"""

import logging
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import AgentRun, Ticket, TicketEvent, User
from app.db.types import utcnow
from app.domain.enums import (
    ACTIVE_RUN_STATUSES,
    ActorType,
    AgentRunStatus,
    TicketCategory,
    TicketEventType,
    TicketStatus,
)
from app.domain.errors import ConflictError, InvalidStateTransitionError, NotFoundError
from app.domain.ticket_status import ensure_system_transition
from app.services.proposals import ProposalDraft, ProposalService

logger = logging.getLogger(__name__)

INTERRUPTED = "interrupted"


class AnalysisRunService:
    def __init__(self, session: Session, *, proposal_ttl_hours: int = 48) -> None:
        self.session = session
        self.proposal_ttl_hours = proposal_ttl_hours

    def enqueue(self, ticket_id: int, actor: User) -> AgentRun:
        """Create a queued run and move the ticket to `triaging`, atomically."""
        ticket = self.session.scalar(select(Ticket).where(Ticket.id == ticket_id).with_for_update())
        if ticket is None:
            raise NotFoundError("Ticket", ticket_id)
        # Only `new` tickets can be analyzed; this also rejects a second concurrent request.
        try:
            ensure_system_transition(ticket.status, TicketStatus.TRIAGING)
        except InvalidStateTransitionError as exc:
            raise ConflictError(
                f"#{ticket_id} numaralı talep '{ticket.status.value}' durumunda; yalnızca 'new' "
                "durumundaki talepler analiz edilebilir"
            ) from exc

        run = AgentRun(ticket_id=ticket.id, requested_by=actor.id, status=AgentRunStatus.QUEUED)
        self.session.add(run)
        try:
            self.session.flush()
        except IntegrityError as exc:  # partial unique index: an active run already exists
            self.session.rollback()
            raise ConflictError(
                f"#{ticket_id} numaralı talebin devam eden bir analizi var"
            ) from exc

        self._event(ticket, TicketEventType.ANALYSIS_REQUESTED, ActorType.USER, actor.id,
                    {"run_id": run.id})  # fmt: skip
        self._move_ticket(ticket, TicketStatus.TRIAGING, run.id)
        self.session.commit()
        return run

    def start(self, run_id: int) -> AgentRun | None:
        """Mark a queued run as running. Returns None if it is no longer queued."""
        run = self.session.scalar(select(AgentRun).where(AgentRun.id == run_id).with_for_update())
        if run is None or run.status != AgentRunStatus.QUEUED:
            self.session.rollback()
            return None
        run.status = AgentRunStatus.RUNNING
        run.started_at = utcnow()
        self.session.commit()
        return run

    def complete(
        self,
        run_id: int,
        *,
        result: dict[str, Any],
        outcome: TicketStatus,
        category: TicketCategory,
        model: str,
        prompt_version: str,
        input_tokens: int | None,
        output_tokens: int | None,
        latency_ms: int,
        proposal: ProposalDraft | None = None,
    ) -> AgentRun:
        """Finish a run; a suggested action becomes a pending proposal in the same transaction."""
        run, ticket = self._lock_running(run_id)
        run.status = AgentRunStatus.SUCCEEDED
        run.result = result
        run.model = model
        run.prompt_version = prompt_version
        run.input_tokens = input_tokens
        run.output_tokens = output_tokens
        run.latency_ms = latency_ms
        run.finished_at = utcnow()

        ticket.category = category
        self._event(ticket, TicketEventType.ANALYSIS_COMPLETED, ActorType.SYSTEM, None,
                    {"run_id": run.id, "category": category.value})  # fmt: skip
        self._move_ticket(ticket, outcome, run.id)
        if proposal is not None:
            ProposalService(self.session, ttl_hours=self.proposal_ttl_hours).create_from_run(
                run, ticket, proposal
            )
        self.session.commit()
        return run

    def fail(self, run_id: int, *, code: str, message: str, model: str | None = None) -> AgentRun:
        run, ticket = self._lock_running(run_id)
        run.status = AgentRunStatus.FAILED
        run.error_code = code
        run.error_message = message[:500]
        run.model = run.model or model
        run.finished_at = utcnow()
        self._event(ticket, TicketEventType.ANALYSIS_FAILED, ActorType.SYSTEM, None,
                    {"run_id": run.id, "error_code": code})  # fmt: skip
        self._move_ticket(ticket, TicketStatus.FAILED, run.id)
        self.session.commit()
        return run

    def recover_interrupted(self) -> int:
        """Fail runs left queued/running by a previous process (call once at startup).

        Assumes a single API process owns the in-process worker (ADR-005).
        """
        run_ids = list(
            self.session.scalars(
                select(AgentRun.id).where(AgentRun.status.in_(ACTIVE_RUN_STATUSES))
            )
        )
        for run_id in run_ids:
            self._force_running(run_id)
            self.fail(
                run_id,
                code=INTERRUPTED,
                message="The service restarted before the analysis finished.",
            )
        if run_ids:
            logger.warning("Marked %d interrupted analysis run(s) as failed", len(run_ids))
        return len(run_ids)

    def get(self, run_id: int) -> AgentRun:
        run = self.session.get(AgentRun, run_id)
        if run is None:
            raise NotFoundError("Run", run_id)
        return run

    def list_for_ticket(self, ticket_id: int) -> list[AgentRun]:
        if self.session.get(Ticket, ticket_id) is None:
            raise NotFoundError("Ticket", ticket_id)
        stmt = select(AgentRun).where(AgentRun.ticket_id == ticket_id).order_by(AgentRun.id.desc())
        return list(self.session.scalars(stmt))

    # --- helpers -------------------------------------------------------------------------

    def _lock_running(self, run_id: int) -> tuple[AgentRun, Ticket]:
        run = self.session.scalar(select(AgentRun).where(AgentRun.id == run_id).with_for_update())
        if run is None:
            raise NotFoundError("Run", run_id)
        if run.status != AgentRunStatus.RUNNING:
            raise InvalidStateTransitionError("run", run.status.value, "finished")
        ticket = self.session.scalar(
            select(Ticket).where(Ticket.id == run.ticket_id).with_for_update()
        )
        if ticket is None:  # pragma: no cover - prevented by the foreign key
            raise NotFoundError("Ticket", run.ticket_id)
        return run, ticket

    def _force_running(self, run_id: int) -> None:
        self.session.execute(
            update(AgentRun)
            .where(AgentRun.id == run_id, AgentRun.status == AgentRunStatus.QUEUED)
            .values(status=AgentRunStatus.RUNNING)
        )

    def _move_ticket(self, ticket: Ticket, target: TicketStatus, run_id: int) -> None:
        ensure_system_transition(ticket.status, target)
        change = {"from": ticket.status.value, "to": target.value, "run_id": run_id}
        self._event(ticket, TicketEventType.STATUS_CHANGED, ActorType.SYSTEM, None, change)
        ticket.status = target

    def _event(
        self,
        ticket: Ticket,
        event_type: TicketEventType,
        actor_type: ActorType,
        actor_id: int | None,
        payload: dict[str, Any],
    ) -> None:
        self.session.add(
            TicketEvent(
                ticket_id=ticket.id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                payload=payload,
            )
        )
