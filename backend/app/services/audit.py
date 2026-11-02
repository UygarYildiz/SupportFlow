"""Append-only audit trail: who proposed, approved, rejected or executed what, and why."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.domain.enums import ActorType

# Keys whose values are personal data. The business record keeps them; the audit log
# only needs to prove that a change happened, not to replicate customer data.
_PII_KEYS = frozenset({"new_address", "current_address", "shipping_address", "email"})
REDACTED = "[redacted]"


def redact(details: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for key, value in details.items():
        if key in _PII_KEYS:
            clean[key] = REDACTED
        elif isinstance(value, dict):
            clean[key] = redact(value)
        else:
            clean[key] = value
    return clean


class AuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        *,
        actor_type: ActorType,
        actor_id: int | None,
        action: str,
        resource_type: str,
        resource_id: object,
        ticket_id: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Add an entry to the current transaction (committed together with the change)."""
        self.session.add(
            AuditLog(
                actor_type=actor_type,
                actor_id=actor_id,
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                ticket_id=ticket_id,
                details=redact(details or {}),
            )
        )

    def list(self, *, ticket_id: int | None, limit: int, offset: int) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.id)
        if ticket_id is not None:
            stmt = stmt.where(AuditLog.ticket_id == ticket_id)
        return list(self.session.scalars(stmt.limit(limit).offset(offset)))
