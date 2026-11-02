"""Human approval and safe execution of proposed actions (ADR-002, ADR-006, ADR-012).

Approval happens in two committed steps:
  1. decision:  pending -> approved -> executing   (who decided and when is recorded)
  2. execution: executing -> executed | failed     (idempotent by key, re-checks the order)
If the process dies between the two, `recover()` finishes step 2 at startup; the
idempotency key guarantees the change is applied at most once.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import ActionProposal, AgentRun, Ticket, TicketEvent, User
from app.domain.enums import (
    ActionType,
    ActorType,
    Decision,
    ExecutionOutcome,
    ProposalStatus,
    TicketEventType,
)
from app.domain.errors import ConflictError, NotFoundError
from app.domain.proposals import ensure_can_decide, ensure_transition, payload_fingerprint
from app.integrations.mock_orders import ActionRequest, MockOrderSystem
from app.services.audit import AuditService

logger = logging.getLogger(__name__)

P = ProposalStatus


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class ProposalDraft:
    """What an analysis suggests. Built by the agent layer from its verified result."""

    action_type: ActionType
    order_id: str
    payload: dict[str, Any]
    reason: str
    policy_rule: str


class ProposalService:
    def __init__(
        self,
        session: Session,
        clock: Callable[[], datetime] = _utcnow,
        ttl_hours: int = 48,
    ) -> None:
        self.session = session
        self.clock = clock
        self.ttl = timedelta(hours=ttl_hours)
        self.audit = AuditService(session)

    # --- creation (called inside the run-completion transaction; no commit here) ---------

    def create_from_run(
        self, run: AgentRun, ticket: Ticket, draft: ProposalDraft
    ) -> ActionProposal:
        for previous in self.session.scalars(
            select(ActionProposal)
            .where(ActionProposal.ticket_id == ticket.id, ActionProposal.status == P.PENDING)
            .with_for_update()
        ):
            self._expire(previous, reason=f"Superseded by analysis run {run.id}")

        now = self.clock()
        proposal = ActionProposal(
            ticket_id=ticket.id,
            run_id=run.id,
            customer_id=ticket.customer_id,
            order_id=draft.order_id,
            type=draft.action_type,
            payload=draft.payload,
            payload_hash=payload_fingerprint(draft.action_type, draft.order_id, draft.payload),
            reason=draft.reason,
            policy_rule=draft.policy_rule,
            status=P.PENDING,
            version=1,
            created_at=now,
            expires_at=now + self.ttl,
        )
        self.session.add(proposal)
        self.session.flush()
        self._event(proposal, TicketEventType.PROPOSAL_CREATED, ActorType.SYSTEM, None)
        self.audit.record(
            actor_type=ActorType.SYSTEM,
            actor_id=None,
            action="proposal.created",
            resource_type="proposal",
            resource_id=proposal.id,
            ticket_id=ticket.id,
            details={
                "run_id": run.id,
                "type": draft.action_type.value,
                "order_id": draft.order_id,
                "policy_rule": draft.policy_rule,
                "payload": draft.payload,
            },
        )
        return proposal

    # --- queries -------------------------------------------------------------------------

    def list(
        self, *, status: ProposalStatus | None, ticket_id: int | None, limit: int, offset: int
    ) -> tuple[list[ActionProposal], int]:
        conditions = []
        if status is not None:
            conditions.append(ActionProposal.status == status)
        if ticket_id is not None:
            conditions.append(ActionProposal.ticket_id == ticket_id)
        total = self.session.scalar(select(func.count(ActionProposal.id)).where(*conditions)) or 0
        stmt = (
            select(ActionProposal)
            .where(*conditions)
            .order_by(ActionProposal.created_at, ActionProposal.id)
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt)), total

    def get(self, proposal_id: int) -> ActionProposal:
        proposal = self.session.get(ActionProposal, proposal_id)
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)
        return proposal

    # --- decision ------------------------------------------------------------------------

    def decide(
        self,
        proposal_id: int,
        *,
        decision: Decision,
        expected_version: int,
        note: str | None,
        actor: User,
    ) -> ActionProposal:
        proposal = self._lock(proposal_id)
        ensure_can_decide(actor.role, proposal.type)  # 403 before revealing anything else

        if proposal.version != expected_version:
            self.session.rollback()
            raise ConflictError(
                f"Proposal {proposal_id} changed (now version {proposal.version}, "
                f"status '{proposal.status.value}'); reload before deciding"
            )
        if proposal.status != P.PENDING:
            self.session.rollback()
            raise ConflictError(f"Proposal {proposal_id} is already '{proposal.status.value}'")
        if self.clock() > proposal.expires_at:
            self._expire(proposal, reason="Not decided before the deadline")
            self.session.commit()
            raise ConflictError(f"Proposal {proposal_id} has expired")

        if decision == Decision.REJECT:
            self._decided(proposal, P.REJECTED, actor, note)
            self._event(proposal, TicketEventType.PROPOSAL_REJECTED, ActorType.USER, actor.id)
            self._audit(proposal, "proposal.rejected", actor.id, {"note": note})
            self.session.commit()
            return proposal

        current = payload_fingerprint(proposal.type, proposal.order_id, proposal.payload)
        if current != proposal.payload_hash:
            self._audit(proposal, "proposal.integrity_failed", actor.id, {})
            self.session.commit()
            raise ConflictError(
                f"Proposal {proposal_id} payload changed after it was proposed; "
                "a new proposal is required"
            )

        # Step 1: record the decision durably before touching the order.
        self._decided(proposal, P.APPROVED, actor, note)
        self._event(proposal, TicketEventType.PROPOSAL_APPROVED, ActorType.USER, actor.id)
        self._audit(proposal, "proposal.approved", actor.id, {"note": note})
        self._move(proposal, P.EXECUTING)
        self.session.commit()

        # Step 2: execute.
        return self._execute(proposal_id, actor_id=actor.id)

    # --- startup recovery ----------------------------------------------------------------

    def recover(self) -> tuple[int, int]:
        """Expire overdue proposals and finish executions interrupted by a restart."""
        overdue = list(
            self.session.scalars(
                select(ActionProposal)
                .where(ActionProposal.status == P.PENDING, ActionProposal.expires_at < self.clock())
                .with_for_update()
            )
        )
        for proposal in overdue:
            self._expire(proposal, reason="Not decided before the deadline")
        self.session.commit()

        executing = list(
            self.session.scalars(
                select(ActionProposal.id).where(ActionProposal.status == P.EXECUTING)
            )
        )
        for proposal_id in executing:
            self._execute(proposal_id, actor_id=None)
        if overdue or executing:
            logger.warning(
                "Proposal recovery: %d expired, %d executions reconciled",
                len(overdue),
                len(executing),
            )
        return len(overdue), len(executing)

    # --- internals -----------------------------------------------------------------------

    def _execute(self, proposal_id: int, *, actor_id: int | None) -> ActionProposal:
        proposal = self._lock(proposal_id)
        if proposal.status != P.EXECUTING:  # already finished by someone else
            self.session.rollback()
            return proposal
        request = ActionRequest(
            proposal_id=proposal.id,
            action_type=proposal.type,
            customer_id=proposal.customer_id,
            order_id=proposal.order_id,
            payload=proposal.payload,
            policy_rule=proposal.policy_rule,
            idempotency_key=f"proposal-{proposal.id}",
            actor_id=actor_id,
        )
        try:
            result = MockOrderSystem(self.session, self.clock).apply(request)
        except Exception:
            # The mock system lives in our database, so rolling back means nothing was
            # applied and `failed` is accurate. A real external system would need an
            # "unknown" outcome reconciled through its idempotency key instead.
            logger.exception("Executing proposal %s failed", proposal_id)
            self.session.rollback()
            proposal = self._lock(proposal_id)
            self._finish(proposal, P.FAILED, "Execution error; nothing was changed", actor_id, {})
            self.session.commit()
            return proposal

        if result.outcome == ExecutionOutcome.SUCCEEDED:
            self._finish(
                proposal, P.EXECUTED, None, actor_id, {"external_ref": result.external_ref}
            )
        else:
            reason = str(result.detail.get("reason", "Rejected by the order system"))
            self._finish(proposal, P.FAILED, reason, actor_id, result.detail)
        self.session.commit()
        return proposal

    def _finish(
        self,
        proposal: ActionProposal,
        status: ProposalStatus,
        failure_reason: str | None,
        actor_id: int | None,
        details: dict[str, Any],
    ) -> None:
        self._move(proposal, status)
        proposal.failure_reason = failure_reason
        if status == P.EXECUTED:
            proposal.executed_at = self.clock()
        event = (
            TicketEventType.ACTION_EXECUTED
            if status == P.EXECUTED
            else TicketEventType.ACTION_FAILED
        )
        self._event(proposal, event, ActorType.SYSTEM, None, {"reason": failure_reason})
        action = "action.executed" if status == P.EXECUTED else "action.failed"
        self._audit(proposal, action, actor_id, {**details, "failure_reason": failure_reason})

    def _decided(
        self, proposal: ActionProposal, status: ProposalStatus, actor: User, note: str | None
    ) -> None:
        self._move(proposal, status)
        proposal.decided_by = actor.id
        proposal.decided_at = self.clock()
        proposal.decision_note = note

    def _expire(self, proposal: ActionProposal, *, reason: str) -> None:
        self._move(proposal, P.EXPIRED)
        proposal.failure_reason = reason
        self._event(
            proposal, TicketEventType.PROPOSAL_EXPIRED, ActorType.SYSTEM, None, {"reason": reason}
        )
        self._audit(proposal, "proposal.expired", None, {"reason": reason})

    def _move(self, proposal: ActionProposal, target: ProposalStatus) -> None:
        ensure_transition(proposal.status, target)
        proposal.status = target
        proposal.version += 1

    def _lock(self, proposal_id: int) -> ActionProposal:
        proposal = self.session.scalar(
            select(ActionProposal)
            .where(ActionProposal.id == proposal_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if proposal is None:
            raise NotFoundError("Proposal", proposal_id)
        return proposal

    def _event(
        self,
        proposal: ActionProposal,
        event_type: TicketEventType,
        actor_type: ActorType,
        actor_id: int | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.session.add(
            TicketEvent(
                ticket_id=proposal.ticket_id,
                event_type=event_type,
                actor_type=actor_type,
                actor_id=actor_id,
                payload={"proposal_id": proposal.id, "type": proposal.type.value, **(extra or {})},
            )
        )

    def _audit(
        self, proposal: ActionProposal, action: str, actor_id: int | None, details: dict[str, Any]
    ) -> None:
        self.audit.record(
            actor_type=ActorType.USER if actor_id is not None else ActorType.SYSTEM,
            actor_id=actor_id,
            action=action,
            resource_type="proposal",
            resource_id=proposal.id,
            ticket_id=proposal.ticket_id,
            details={"order_id": proposal.order_id, "status": proposal.status.value, **details},
        )
