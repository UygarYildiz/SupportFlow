from fastapi import APIRouter

from app.api.deps import AdminUser, DbSession
from app.schemas.auth import UserOut
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(_: AdminUser, session: DbSession) -> list[UserOut]:
    """Support staff accounts. Admin only."""
    return [UserOut.model_validate(user) for user in UserService(session).list_users()]
