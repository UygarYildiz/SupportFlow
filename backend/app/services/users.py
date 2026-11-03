from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.db.models import User
from app.domain.accounts import ensure_an_admin_remains, normalize_email, validate_new_password
from app.domain.enums import ActorType, UserRole
from app.domain.errors import BusinessRuleViolationError, ConflictError, NotFoundError
from app.services.audit import AuditService

_DUPLICATE_EMAIL = "Bu e-posta adresiyle bir hesap zaten var"


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

    def count_users(self) -> int:
        return self.session.scalar(select(func.count()).select_from(User)) or 0

    def add_user(self, *, email: str, full_name: str, role: UserRole, password: str) -> User:
        """Insert an account in the current transaction (no commit, no audit).

        Shared by `create` and the first-run setup, which commit it together with
        their own records.
        """
        email = normalize_email(email)
        full_name = full_name.strip()
        if not full_name:
            raise BusinessRuleViolationError("Ad soyad boş olamaz")
        validate_new_password(password, email=email)
        if self._find_by_email(email) is not None:
            raise ConflictError(_DUPLICATE_EMAIL)
        user = User(
            email=email, full_name=full_name, role=role, password_hash=hash_password(password)
        )
        self.session.add(user)
        try:
            with self.session.begin_nested():
                self.session.flush()
        except IntegrityError:
            # Another request created the same address between the check and the insert.
            raise ConflictError(_DUPLICATE_EMAIL) from None
        return user

    def create(
        self, *, email: str, full_name: str, role: UserRole, password: str, actor: User
    ) -> User:
        user = self.add_user(email=email, full_name=full_name, role=role, password=password)
        self._audit(actor, "user.created", user, {"role": role.value})
        self.session.commit()
        return user

    def update(
        self,
        user_id: int,
        *,
        actor: User,
        full_name: str | None = None,
        role: UserRole | None = None,
        is_active: bool | None = None,
        password: str | None = None,
    ) -> User:
        """Admin edits an account (their own: name and password only).

        Role and activity changes first lock every active admin row (in id order), so
        two concurrent demotions serialize and cannot both leave zero admins.
        """
        if role is not None or is_active is not None:
            self._lock_active_admins()
        user = self.session.get(User, user_id, with_for_update=True)
        if user is None:
            raise NotFoundError("User", user_id)
        changes: dict[str, object] = {}

        if user.id == actor.id and (is_active is False or (role and role != user.role)):
            raise BusinessRuleViolationError(
                "Kendi rolünüzü değiştiremez ya da hesabınızı pasifleştiremezsiniz"
            )
        if full_name is not None and full_name.strip() != user.full_name:
            if not full_name.strip():
                raise BusinessRuleViolationError("Ad soyad boş olamaz")
            user.full_name = full_name.strip()
            changes["full_name"] = True
        if role is not None and role != user.role:
            changes["role"] = role.value
            user.role = role
        if is_active is not None and is_active != user.is_active:
            changes["is_active"] = is_active
            user.is_active = is_active
        if password is not None:
            validate_new_password(password, email=user.email)
            user.password_hash = hash_password(password)
            changes["password_reset"] = True

        if "role" in changes or "is_active" in changes:
            self.session.flush()
            try:
                ensure_an_admin_remains(self._active_admin_count())
            except BusinessRuleViolationError:
                self.session.rollback()
                raise
        if changes:
            self._audit(actor, "user.updated", user, changes)
            self.session.commit()
        return user

    def change_own_password(self, user: User, *, current_password: str, new_password: str) -> None:
        if not verify_password(current_password, user.password_hash):
            raise BusinessRuleViolationError("Mevcut parola hatalı")
        if current_password == new_password:
            raise BusinessRuleViolationError("Yeni parola mevcut paroladan farklı olmalı")
        validate_new_password(new_password, email=user.email)
        user.password_hash = hash_password(new_password)
        self._audit(user, "user.password_changed", user, {})
        self.session.commit()

    def _find_by_email(self, email: str) -> User | None:
        return self.session.scalar(select(User).where(func.lower(User.email) == email.lower()))

    def _active_admins(self) -> Select[int]:
        return select(User.id).where(User.role == UserRole.ADMIN, User.is_active.is_(True))

    def _lock_active_admins(self) -> None:
        self.session.scalars(self._active_admins().order_by(User.id).with_for_update()).all()

    def _active_admin_count(self) -> int:
        return len(self.session.scalars(self._active_admins()).all())

    def _audit(self, actor: User, action: str, user: User, details: dict[str, object]) -> None:
        AuditService(self.session).record(
            actor_type=ActorType.USER,
            actor_id=actor.id,
            action=action,
            resource_type="user",
            resource_id=user.id,
            details=details,
        )
