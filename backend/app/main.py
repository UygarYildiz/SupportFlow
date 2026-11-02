"""FastAPI application factory."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.exc import SQLAlchemyError

from app.api import health
from app.api.errors import register_exception_handlers
from app.api.v1 import api_router
from app.core.config import get_settings
from app.db.session import session_scope
from app.services.analysis_runs import AnalysisRunService
from app.services.proposals import ProposalService

logger = logging.getLogger(__name__)


def _recover_interrupted_work() -> None:
    """Single-process assumption (ADR-005): nothing else is running work right now."""
    try:
        with session_scope() as session:
            AnalysisRunService(session).recover_interrupted()
            ProposalService(session, ttl_hours=get_settings().proposal_ttl_hours).recover()
    except SQLAlchemyError:
        # Don't block startup: /ready reports the database problem.
        logger.exception("Could not recover interrupted work")


def create_app(*, recover_interrupted_runs: bool = True) -> FastAPI:
    """`recover_interrupted_runs=False` is for tests, which manage their own database."""
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if recover_interrupted_runs:
            _recover_interrupted_work()
        yield

    app = FastAPI(
        title="SupportFlow AI",
        version="0.1.0",
        description="Support operations API with AI-drafted proposals and human approval.",
        lifespan=lifespan,
    )
    register_exception_handlers(app)
    app.include_router(health.router)
    app.include_router(api_router)
    return app


app = create_app()
