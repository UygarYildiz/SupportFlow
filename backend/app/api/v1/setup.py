"""First-run setup (ADR-017). Both endpoints are public by design: before setup there
is no account to authenticate with. `POST` works exactly once per installation."""

from fastapi import APIRouter, status

from app.api.deps import AppSettings, DbSession
from app.core.config import Settings
from app.core.security import create_access_token
from app.schemas.auth import TokenResponse
from app.schemas.common import ErrorResponse
from app.schemas.setup import SetupRequest, SetupStatusOut
from app.services.setup import SetupService

router = APIRouter(prefix="/setup", tags=["setup"])


def _service(session: DbSession, settings: Settings) -> SetupService:
    token = settings.setup_token.get_secret_value() if settings.setup_token else None
    return SetupService(session, mode=settings.deployment_mode, setup_token=token)


@router.get("/status")
def setup_status(session: DbSession, settings: AppSettings) -> SetupStatusOut:
    """Which mode the installation runs in and whether it still needs its first admin."""
    current = _service(session, settings).status()
    return SetupStatusOut(
        mode=current.mode,
        setup_required=current.setup_required,
        setup_token_required=current.setup_token_required,
        organization_name=current.organization_name,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)
def complete_setup(body: SetupRequest, session: DbSession, settings: AppSettings) -> TokenResponse:
    """Create the business record and its first admin, and sign that admin in."""
    admin = _service(session, settings).complete(
        organization_name=body.organization_name,
        full_name=body.full_name,
        email=body.email,
        password=body.password,
        setup_token=body.setup_token,
    )
    token = create_access_token(admin.id, admin.role, settings)
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60)
