"""Runs one queued analysis end to end (in-process worker, ADR-005).

Guarantee: whatever happens, a started run ends as `succeeded` or `failed`;
it is never left `running` while this process is alive.
"""

import logging
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agent.analyzer import AnalysisError, TicketAnalyzer
from app.agent.facts import gather_facts
from app.agent.llm.base import LLMClient
from app.db.models import Ticket
from app.services.analysis_runs import AnalysisRunService

logger = logging.getLogger(__name__)

SessionScope = Callable[[], AbstractContextManager[Session]]


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AnalysisExecutor:
    def __init__(
        self,
        session_scope: SessionScope,
        llm: LLMClient,
        clock: Callable[[], datetime] = _utcnow,
    ) -> None:
        self.session_scope = session_scope
        self.analyzer = TicketAnalyzer(llm)
        self.llm = llm
        self.clock = clock

    def execute(self, run_id: int) -> None:
        with self.session_scope() as session:
            runs = AnalysisRunService(session)
            run = runs.start(run_id)
            if run is None:
                logger.info("Run %s is no longer queued; skipping", run_id)
                return
            try:
                ticket = session.get(Ticket, run.ticket_id)
                if ticket is None:  # pragma: no cover - prevented by the foreign key
                    raise AnalysisError("ticket_missing", "Ticket no longer exists")
                facts = gather_facts(session, ticket, self.clock())
                # Close the read transaction before the slow LLM call.
                session.commit()
                result, metrics = self.analyzer.analyze(facts)
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
                "Analysis run %s succeeded: ticket=%s outcome=%s latency_ms=%s",
                run_id,
                run.ticket_id,
                result.outcome_status.value,
                metrics.latency_ms,
            )
