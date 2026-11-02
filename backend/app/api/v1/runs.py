from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, status

from app.agent.executor import AnalysisExecutor
from app.agent.llm.factory import build_llm_client
from app.api.deps import DbSession, StaffUser
from app.core.config import get_settings
from app.db.session import session_scope
from app.schemas.common import ErrorResponse
from app.schemas.runs import RunOut
from app.services.analysis_runs import AnalysisRunService

router = APIRouter(tags=["analysis"])


@lru_cache
def get_analysis_executor() -> AnalysisExecutor:
    """One executor per process; tests override this dependency."""
    return AnalysisExecutor(session_scope, build_llm_client(get_settings()))


Executor = Annotated[AnalysisExecutor, Depends(get_analysis_executor)]

_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
    status.HTTP_409_CONFLICT: {"model": ErrorResponse},
}


@router.post(
    "/tickets/{ticket_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    responses=_ERRORS,
)
def analyze_ticket(
    ticket_id: int,
    user: StaffUser,
    session: DbSession,
    executor: Executor,
    background: BackgroundTasks,
) -> RunOut:
    """Queue an AI analysis. Poll `GET /runs/{id}` for the result.

    409 if the ticket is not `new` or an analysis is already in progress.
    """
    run = AnalysisRunService(session).enqueue(ticket_id, user)
    background.add_task(executor.execute, run.id)
    return RunOut.model_validate(run)


@router.get("/runs/{run_id}", responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}})
def get_run(run_id: int, _: StaffUser, session: DbSession) -> RunOut:
    return RunOut.model_validate(AnalysisRunService(session).get(run_id))


@router.get(
    "/tickets/{ticket_id}/runs", responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}
)
def list_ticket_runs(ticket_id: int, _: StaffUser, session: DbSession) -> list[RunOut]:
    runs = AnalysisRunService(session).list_for_ticket(ticket_id)
    return [RunOut.model_validate(run) for run in runs]
