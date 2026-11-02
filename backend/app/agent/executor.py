"""Runs one queued analysis end to end (in-process worker, ADR-005).

Guarantee: whatever happens, a started run ends as `succeeded` or `failed`;
it is never left `running` while this process is alive.
"""

import logging
import time
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.agent.graph import (
    AnalysisError,
    AnalysisGraph,
    GraphDeps,
    TokenBudget,
    mentioned_order_ids,
)
from app.agent.llm.base import LLMClient
from app.agent.schemas import TicketSnapshot
from app.agent.tools import DatabaseTools
from app.db.models import AgentRunStep, Customer, Ticket
from app.services.analysis_runs import AnalysisRunService

logger = logging.getLogger(__name__)

SessionScope = Callable[[], AbstractContextManager[Session]]


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class DatabaseStepRecorder:
    """Persists each graph step right away, so progress is visible while the run is going."""

    session: Session
    run_id: int
    sequence: int = 0

    def record(self, node: str, status: str, summary: dict[str, Any], duration_ms: int) -> None:
        self.sequence += 1
        self.session.add(
            AgentRunStep(
                run_id=self.run_id,
                sequence=self.sequence,
                node=node,
                status=status,
                summary=summary,
                duration_ms=duration_ms,
            )
        )
        # Also ends the read transaction before the next (possibly slow) LLM call.
        self.session.commit()


class AnalysisExecutor:
    def __init__(
        self,
        session_scope: SessionScope,
        llm: LLMClient,
        clock: Callable[[], datetime] = _utcnow,
        *,
        max_tokens_per_run: int = 12_000,
        run_timeout_seconds: float = 120.0,
    ) -> None:
        self.session_scope = session_scope
        self.llm = llm
        self.clock = clock
        self.max_tokens_per_run = max_tokens_per_run
        self.run_timeout_seconds = run_timeout_seconds

    def execute(self, run_id: int) -> None:
        with self.session_scope() as session:
            runs = AnalysisRunService(session)
            run = runs.start(run_id)
            if run is None:
                logger.info("Run %s is no longer queued; skipping", run_id)
                return
            graph = AnalysisGraph(self._deps(session, run_id))
            try:
                result, metrics = graph.run(run.ticket_id)
            except AnalysisError as exc:
                logger.warning("Analysis run %s failed: %s", run_id, exc.code)
                session.rollback()
                runs.fail(run_id, code=exc.code, message=str(exc), model=self.llm.model_name)
                return
            except Exception:
                logger.exception("Analysis run %s crashed", run_id)
                session.rollback()
                runs.fail(
                    run_id,
                    code="internal_error",
                    message="Unexpected error during analysis",
                    model=self.llm.model_name,
                )
                return

            runs.complete(
                run_id,
                result=result.model_dump(mode="json"),
                outcome=result.outcome_status,
                category=result.analysis.category,
                model=metrics.model,
                prompt_version=result.prompt_version,
                input_tokens=metrics.input_tokens,
                output_tokens=metrics.output_tokens,
                latency_ms=metrics.latency_ms,
            )
            logger.info(
                "Analysis run %s succeeded: ticket=%s outcome=%s action=%s",
                run_id,
                run.ticket_id,
                result.outcome_status.value,
                result.proposed_action.type.value if result.proposed_action else None,
            )

    def _deps(self, session: Session, run_id: int) -> GraphDeps:
        def load_ticket(ticket_id: int) -> TicketSnapshot:
            ticket = session.get(Ticket, ticket_id)
            if ticket is None:  # pragma: no cover - prevented by the foreign key
                raise AnalysisError("ticket_missing", "Ticket no longer exists")
            customer = session.get(Customer, ticket.customer_id)
            return TicketSnapshot(
                ticket_id=ticket.id,
                customer_id=ticket.customer_id,
                customer_name=customer.display_name if customer else "customer",
                subject=ticket.subject,
                message=ticket.message,
                linked_order_id=ticket.order_id,
                mentioned_order_ids=mentioned_order_ids(f"{ticket.subject} {ticket.message}"),
            )

        return GraphDeps(
            llm=self.llm,
            load_ticket=load_ticket,
            tools_for=lambda customer_id: DatabaseTools(session, customer_id, self.clock),
            recorder=DatabaseStepRecorder(session, run_id),
            clock=self.clock,
            budget=TokenBudget(self.max_tokens_per_run),
            deadline=time.monotonic() + self.run_timeout_seconds,
        )
