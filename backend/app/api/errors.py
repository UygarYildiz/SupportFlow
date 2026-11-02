"""Map domain errors to HTTP responses in one place."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.domain.errors import (
    BusinessRuleViolationError,
    DomainError,
    InvalidStateTransitionError,
    NotFoundError,
)

_STATUS_BY_ERROR: list[tuple[type[DomainError], int]] = [
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (InvalidStateTransitionError, status.HTTP_409_CONFLICT),
    (BusinessRuleViolationError, status.HTTP_422_UNPROCESSABLE_CONTENT),
]


async def _handle_domain_error(_: Request, exc: Exception) -> JSONResponse:
    code = next(
        (code for error_type, code in _STATUS_BY_ERROR if isinstance(exc, error_type)),
        status.HTTP_400_BAD_REQUEST,
    )
    return JSONResponse(status_code=code, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _handle_domain_error)
