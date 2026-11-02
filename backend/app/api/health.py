"""Liveness and readiness probes. Both are public (no auth) by design."""

import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_engine, ping_database

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database: Literal["ok", "unavailable"]


@router.get("/health")
def health() -> HealthResponse:
    """Liveness: the process is up. Does not touch dependencies."""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def ready(response: Response, engine: Annotated[Engine, Depends(get_engine)]) -> ReadinessResponse:
    """Readiness: the service can handle traffic, i.e. the database answers."""
    try:
        ping_database(engine)
    except SQLAlchemyError:
        # Log the cause for operators; never return driver details to the client.
        logger.exception("Readiness check failed: database unavailable")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(status="not_ready", database="unavailable")
    return ReadinessResponse(status="ready", database="ok")
