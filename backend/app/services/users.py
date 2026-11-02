from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.models import User


class UserService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def authenticate(self, email: str, password: str) -> User | None:
        """Return the active user for valid credentials, else None.

        Unknown e-mail, wrong password and inactive account all look the same
        to the caller, so the API cannot be used to discover accounts.
        """
        user = self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))
        password_ok = verify_password(password, user.password_hash if user else None)
        if user is None or not password_ok or not user.is_active:
            return None
        return user

    def get_active(self, user_id: int) -> User | None:
        user = self.session.get(User, user_id)
        return user if user is not None and user.is_active else None

    def list_users(self) -> list[User]:
        return list(self.session.scalars(select(User).order_by(User.id)))
