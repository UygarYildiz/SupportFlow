from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query, status

from app.api.deps import AdminUser, AppSettings, DbSession, StaffUser
from app.db.models import ActionProposal, User
from app.domain.enums import ProposalStatus
from app.domain.proposals import can_decide
from app.schemas.common import ErrorResponse, Page
from app.schemas.proposals import AuditLogOut, DecisionRequest, ProposalOut
from app.services.audit import AuditService
from app.services.proposals import ProposalService

router = APIRouter(tags=["approvals"])


def _out(proposal: ActionProposal, user: User) -> ProposalOut:
    return ProposalOut.model_validate(proposal).model_copy(
        update={"can_decide": can_decide(user.role, proposal.type)}
    )


@router.get("/proposals")
def list_proposals(
    user: StaffUser,
    session: DbSession,
    status_filter: Annotated[ProposalStatus | None, Query(alias="status")] = None,
    ticket_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ProposalOut]:
    """Approval queue: `?status=pending` lists what waits for a decision."""
    items, total = ProposalService(session).list(
        status=status_filter, ticket_id=ticket_id, limit=limit, offset=offset
    )
    return Page(items=[_out(p, user) for p in items], total=total, limit=limit, offset=offset)


@router.get("/proposals/{proposal_id}", responses={404: {"model": ErrorResponse}})
def get_proposal(proposal_id: int, user: StaffUser, session: DbSession) -> ProposalOut:
    return _out(ProposalService(session).get(proposal_id), user)


_DECISION_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Role may not decide"},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_409_CONFLICT: {
        "model": ErrorResponse,
        "description": "Stale version, already decided, expired, or payload changed",
    },
}


@router.post("/proposals/{proposal_id}/decision", responses=_DECISION_ERRORS)
def decide_proposal(
    proposal_id: int,
    body: DecisionRequest,
    user: StaffUser,
    session: DbSession,
    settings: AppSettings,
) -> ProposalOut:
    """Approve or reject. Approval executes the action immediately, exactly once.

    The resulting status is `executed`, `failed` (e.g. the order shipped in the
    meantime) or `rejected`. Repeating a decision returns 409 and changes nothing.
    """
    service = ProposalService(session, ttl_hours=settings.proposal_ttl_hours)
    proposal = service.decide(
        proposal_id,
        decision=body.decision,
        expected_version=body.expected_version,
        note=body.note,
        actor=user,
    )
    return _out(proposal, user)


@router.get("/audit")
def list_audit_logs(
    _: AdminUser,
    session: DbSession,
    ticket_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    sort: Annotated[
        Literal["oldest", "newest"],
        Query(description="Chronological (default) or newest first, for recent activity"),
    ] = "oldest",
) -> list[AuditLogOut]:
    """Audit trail (admin only). Personal data in details is redacted."""
    entries = AuditService(session).list(
        ticket_id=ticket_id, limit=limit, offset=offset, newest_first=sort == "newest"
    )
    return [AuditLogOut.model_validate(entry) for entry in entries]
