from fastapi import APIRouter, HTTPException, status

from app.api.deps import AppSettings, CurrentUser, DbSession
from app.core.security import create_access_token
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.schemas.common import ErrorResponse
from app.services.users import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
def login(body: LoginRequest, session: DbSession, settings: AppSettings) -> TokenResponse:
    user = UserService(session).authenticate(body.email, body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user.id, user.role, settings)
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60)


@router.get("/me")
def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
