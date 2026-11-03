from typing import Any

from fastapi import APIRouter, status

from app.api.deps import AdminUser, DbSession
from app.schemas.auth import UserCreate, UserOut, UserUpdate
from app.schemas.common import ErrorResponse
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])

_ERRORS: dict[int | str, dict[str, Any]] = {
    status.HTTP_409_CONFLICT: {"model": ErrorResponse},
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
}


@router.get("")
def list_users(_: AdminUser, session: DbSession) -> list[UserOut]:
    """Support staff accounts. Admin only."""
    return [UserOut.model_validate(user) for user in UserService(session).list_users()]


@router.post("", status_code=status.HTTP_201_CREATED, responses=_ERRORS)
def create_user(body: UserCreate, admin: AdminUser, session: DbSession) -> UserOut:
    """Add a staff account with an initial password. Admin only."""
    user = UserService(session).create(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        password=body.password,
        actor=admin,
    )
    return UserOut.model_validate(user)


@router.patch(
    "/{user_id}",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}, **_ERRORS},
)
def update_user(user_id: int, body: UserUpdate, admin: AdminUser, session: DbSession) -> UserOut:
    """Rename, change role, (de)activate or reset the password of an account. Admin only."""
    user = UserService(session).update(
        user_id,
        actor=admin,
        full_name=body.full_name,
        role=body.role,
        is_active=body.is_active,
        password=body.password,
    )
    return UserOut.model_validate(user)
