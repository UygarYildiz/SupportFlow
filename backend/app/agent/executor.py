"""Runs one queued analysis end to end (in-process worker, ADR-005).

Guarantee: whatever happens, a started run ends as `succeeded` or `failed`;
it is never left `running` while this process is alive.
"""

import logging
import time
from collections.abc import Callable
from contextlib import AbstractContextManager, nullcontext
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.agent.graph import (
    AnalysisError,
    AnalysisGraph,
    GraphDeps,
    TokenBudget,
    mentioned_order_ids,
)
from app.agent.llm.base import LLMClient
from app.agent.llm.fake_embeddings import FakeEmbedder
from app.agent.mcp_tools import McpAgentTools
from app.agent.schemas import ProposedAction, TicketSnapshot
from app.agent.tools import AgentTools, DatabaseTools
from app.db.models import AgentRunStep, Customer, Ticket
from app.db.models.knowledge import EMBEDDING_DIMENSIONS
from app.mcp.access import agent_run_authenticator
from app.mcp.server import build_server
from app.services.analysis_runs import AnalysisRunService
from app.services.policy_knowledge import Embedder
from app.services.proposals import ProposalDraft

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
        proposal_ttl_hours: int = 48,
        embedder: Embedder | None = None,
        tool_transport: Literal["mcp", "direct"] = "mcp",
        tool_timeout_seconds: float = 10.0,
    ) -> None:
        self.session_scope = session_scope
        self.llm = llm
        # Policy search (ADR-014); the offline embedder unless the app configures another.
        self.embedder = embedder or FakeEmbedder(EMBEDDING_DIMENSIONS)
        self.clock = clock
        self.max_tokens_per_run = max_tokens_per_run
        self.run_timeout_seconds = run_timeout_seconds
        self.proposal_ttl_hours = proposal_ttl_hours
        self.tool_transport = tool_transport
        self.tool_timeout_seconds = tool_timeout_seconds

    def execute(self, run_id: int) -> None:
        with self.session_scope() as session:
            runs = AnalysisRunService(session, proposal_ttl_hours=self.proposal_ttl_hours)
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
                    message="Analiz sırasında beklenmeyen bir hata oluştu",
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
                proposal=_draft(result.proposed_action),
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
                raise AnalysisError("ticket_missing", "Talep artık mevcut değil")
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
            tools_for=lambda ticket: self._tools(session, run_id, ticket),
            recorder=DatabaseStepRecorder(session, run_id),
            clock=self.clock,
            budget=TokenBudget(self.max_tokens_per_run),
            deadline=time.monotonic() + self.run_timeout_seconds,
        )

    def _tools(self, session: Session, run_id: int, ticket: TicketSnapshot) -> AgentTools:
        local = DatabaseTools(session, ticket.customer_id, self.clock, embedder=self.embedder)
        if self.tool_transport == "direct":
            return local
        # The run's own MCP connection: it shares the run's session (and transaction)
        # and may read only this ticket (ADR-015).
        server = build_server(
            session_scope=lambda: nullcontext(session),
            authenticate=agent_run_authenticator(ticket.ticket_id, run_id),
            audit_calls=False,
        )
        return McpAgentTools(
            local=local,
            server=server,
            ticket_id=ticket.ticket_id,
            timeout_seconds=self.tool_timeout_seconds,
        )


def _draft(action: ProposedAction | None) -> ProposalDraft | None:
    """Hand the verified suggestion to the service layer, which never imports agent types."""
    if action is None:
        return None
    return ProposalDraft(
        action_type=action.type,
        order_id=action.order_id,
        payload=action.payload,
        reason=action.reason,
        policy_rule=action.policy_rule,
    )
