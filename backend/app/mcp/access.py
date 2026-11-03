"""Who is calling an MCP tool, and may they read this ticket? (ADR-015)

Identity comes from the connection, never from tool arguments:

- `StaffPrincipal`: a stdio client started with a staff member's access token
  (`MCP_ACCESS_TOKEN`). The token is verified and the user re-read from the database
  on every call, so an expired token or a deactivated user stops working at once.
- `AgentRunPrincipal`: the in-process connection of one analysis run. It may read
  only the ticket it is analysing.

A `ticket_id` argument only names what to read; `authorize` decides whether that
is allowed, and the ticket row (not the caller) decides which customer is in scope.
"""

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import InvalidTokenError, decode_access_token
from app.domain.enums import UserRole
from app.services.users import UserService

STAFF_ROLES = frozenset({UserRole.AGENT_USER, UserRole.ADMIN})


@dataclass(frozen=True)
class StaffPrincipal:
    user_id: int
    role: UserRole


@dataclass(frozen=True)
class AgentRunPrincipal:
    ticket_id: int
    run_id: int | None


Principal = StaffPrincipal | AgentRunPrincipal

# Resolves the caller for one tool call, inside that call's database session.
Authenticator = Callable[[Session], Principal]


class ToolAccessError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code  # "unauthorized" | "forbidden"


def staff_token_authenticator(token: SecretStr, settings: Settings) -> Authenticator:
    def authenticate(session: Session) -> Principal:
        try:
            claims = decode_access_token(token.get_secret_value(), settings)
        except InvalidTokenError:
            raise ToolAccessError(
                "unauthorized", "Erişim anahtarı geçersiz ya da süresi dolmuş"
            ) from None
        user = UserService(session).get_active(claims.user_id)
        if user is None:
            raise ToolAccessError("unauthorized", "Kullanıcı bulunamadı ya da devre dışı")
        if user.role not in STAFF_ROLES:
            raise ToolAccessError("forbidden", "Bu araçları kullanma yetkiniz yok")
        return StaffPrincipal(user_id=user.id, role=user.role)

    return authenticate


def agent_run_authenticator(ticket_id: int, run_id: int | None) -> Authenticator:
    principal = AgentRunPrincipal(ticket_id=ticket_id, run_id=run_id)
    return lambda _session: principal


def authorize(principal: Principal, ticket_id: int) -> None:
    """Staff may read any ticket (as in the REST API); a run only its own."""
    if isinstance(principal, AgentRunPrincipal) and ticket_id != principal.ticket_id:
        raise ToolAccessError("forbidden", "Bu analiz yalnızca kendi talebini okuyabilir")
