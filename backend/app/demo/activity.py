"""Demo activity: a few seeded tickets already analyzed and one already decided.

Without it a fresh demo opens with every ticket `new` and an empty approval queue,
so the role difference (refunds need an admin) only shows after several clicks.

Everything goes through the real path: queued run -> analysis graph -> pending
proposal -> ProposalService.decide. The LLM is always the deterministic
FakeLLMClient, whatever LLM_MODE says, so seeding never calls a paid API; runs
show `fake-llm` as their model. Ticket 1 (S1) is left `new` for the live demo.
Idempotent: a ticket is only analyzed while it is still `new` with no runs.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.executor import AnalysisExecutor
from app.agent.llm.fake import FakeLLMClient
from app.db.models import ActionProposal, AgentRun, Ticket, User
from app.domain.enums import Decision, ProposalStatus, TicketStatus
from app.services.analysis_runs import AnalysisRunService
from app.services.proposals import ProposalService
from app.services.tickets import TicketService

DEMO_ANALYST = "sam@novashop.example"

# Ticket id -> what the analysis produces with the fake model.
PRE_ANALYZED_TICKETS = (
    2,  # S2 damaged kettle: refund request, waits for an admin
    3,  # S3 address change before shipping: waits for any staff member
    5,  # S4 unknown order ORD-9999: needs_info, nothing invented
    7,  # S5 refund outside the return window: human review, no action
    8,  # return inside the window: refund request, waits for an admin
    14,  # prompt injection: human review, no action
    15,  # address change: Sam approves it below and resolves the ticket
)
APPROVED_BY_ANALYST = (15,)


@dataclass(frozen=True)
class ActivitySummary:
    analyzed: int
    approved: int


def seed_demo_activity(session: Session, clock: Callable[[], datetime]) -> ActivitySummary:
    analyst = session.scalar(select(User).where(User.email == DEMO_ANALYST))
    if analyst is None:
        raise RuntimeError("Seed the demo users before the demo activity")

    @contextmanager
    def scope() -> Iterator[Session]:
        yield session

    executor = AnalysisExecutor(scope, FakeLLMClient(), clock)
    runs = AnalysisRunService(session)
    analyzed = 0
    for ticket_id in PRE_ANALYZED_TICKETS:
        ticket = session.get(Ticket, ticket_id)
        already_ran = session.scalar(select(AgentRun.id).where(AgentRun.ticket_id == ticket_id))
        if ticket is None or ticket.status != TicketStatus.NEW or already_ran is not None:
            continue
        run = runs.enqueue(ticket_id, analyst)
        executor.execute(run.id)
        analyzed += 1

    proposals = ProposalService(session, clock=clock)
    approved = 0
    for ticket_id in APPROVED_BY_ANALYST:
        pending = session.scalar(
            select(ActionProposal).where(
                ActionProposal.ticket_id == ticket_id,
                ActionProposal.status == ProposalStatus.PENDING,
            )
        )
        if pending is None:
            continue
        proposals.decide(
            pending.id,
            decision=Decision.APPROVE,
            expected_version=pending.version,
            note="Customer confirmed the new address by phone.",
            actor=analyst,
        )
        # Applying a change does not close the ticket; staff resolve it, as in the UI.
        TicketService(session).update(
            ticket_id, status=TicketStatus.RESOLVED, priority=None, actor=analyst
        )
        approved += 1
    return ActivitySummary(analyzed=analyzed, approved=approved)
