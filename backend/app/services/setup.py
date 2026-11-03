"""First-run setup of a self-hosted installation (ADR-017).

A fresh `self_hosted` installation has no users. The first visitor creates the
business record and its first admin in one transaction; after that, setup is
closed for good. `demo` installations never offer setup (they are seeded).
"""

import hmac
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Installation, User
from app.domain.enums import ActorType, UserRole
from app.domain.errors import BusinessRuleViolationError, ConflictError, ForbiddenError
from app.services.audit import AuditService
from app.services.users import UserService

DeploymentMode = Literal["demo", "self_hosted"]

_ALREADY_DONE = "Kurulum zaten tamamlanmış. Giriş yapın."


@dataclass(frozen=True)
class SetupStatus:
    mode: DeploymentMode
    setup_required: bool
    setup_token_required: bool
    organization_name: str | None


class SetupService:
    def __init__(self, session: Session, *, mode: DeploymentMode, setup_token: str | None) -> None:
        self.session = session
        self.mode: DeploymentMode = mode
        self.setup_token = setup_token or None

    def status(self) -> SetupStatus:
        installation = self.session.get(Installation, 1)
        return SetupStatus(
            mode=self.mode,
            setup_required=self._setup_open(installation),
            setup_token_required=self.setup_token is not None,
            organization_name=installation.organization_name if installation else None,
        )

    def complete(
        self,
        *,
        organization_name: str,
        full_name: str,
        email: str,
        password: str,
        setup_token: str | None,
    ) -> User:
        """Create the installation record and its first admin, or raise.

        Order matters: the cheap state checks come first, then the token, so a
        finished installation answers 409 to everyone and leaks nothing else.
        """
        if not self._setup_open(self.session.get(Installation, 1)):
            raise ConflictError(_ALREADY_DONE)
        if self.setup_token is not None and not hmac.compare_digest(
            (setup_token or "").encode(), self.setup_token.encode()
        ):
            raise ForbiddenError("Kurulum kodu hatalı")
        organization_name = organization_name.strip()
        if not organization_name:
            raise BusinessRuleViolationError("İşletme adı boş olamaz")

        admin = UserService(self.session).add_user(
            email=email, full_name=full_name, role=UserRole.ADMIN, password=password
        )
        self.session.add(
            Installation(id=1, organization_name=organization_name, completed_by_id=admin.id)
        )
        try:
            self.session.flush()
        except IntegrityError:
            # A concurrent setup inserted the single installation row first.
            self.session.rollback()
            raise ConflictError(_ALREADY_DONE) from None
        AuditService(self.session).record(
            actor_type=ActorType.USER,
            actor_id=admin.id,
            action="setup.completed",
            resource_type="installation",
            resource_id=1,
            details={"organization_name": organization_name},
        )
        self.session.commit()
        return admin

    def _setup_open(self, installation: Installation | None) -> bool:
        # Existing users also close setup: nobody may add an admin to a used database.
        return (
            self.mode == "self_hosted"
            and installation is None
            and UserService(self.session).count_users() == 0
        )
