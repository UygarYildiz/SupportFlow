"""Action proposals: lifecycle, approver rules and payload integrity. Pure Python."""

import hashlib
import json
from typing import Any

from app.domain.enums import ActionType, ProposalStatus, UserRole
from app.domain.errors import ForbiddenError, InvalidStateTransitionError

P = ProposalStatus

TRANSITIONS: dict[ProposalStatus, frozenset[ProposalStatus]] = {
    P.PENDING: frozenset({P.APPROVED, P.REJECTED, P.EXPIRED}),
    P.APPROVED: frozenset({P.EXECUTING}),
    P.EXECUTING: frozenset({P.EXECUTED, P.FAILED}),
    P.EXECUTED: frozenset(),
    P.REJECTED: frozenset(),
    P.FAILED: frozenset(),
    P.EXPIRED: frozenset(),
}

# Who may decide (approve or reject) which kind of action (docs/REQUIREMENTS.md section 3).
APPROVER_ROLES: dict[ActionType, frozenset[UserRole]] = {
    ActionType.CHANGE_SHIPPING_ADDRESS: frozenset({UserRole.AGENT_USER, UserRole.ADMIN}),
    ActionType.CREATE_REFUND_REQUEST: frozenset({UserRole.ADMIN}),
}


def ensure_transition(current: ProposalStatus, target: ProposalStatus) -> None:
    if target not in TRANSITIONS[current]:
        raise InvalidStateTransitionError("proposal", current.value, target.value)


def can_decide(role: UserRole, action_type: ActionType) -> bool:
    return role in APPROVER_ROLES[action_type]


def ensure_can_decide(role: UserRole, action_type: ActionType) -> None:
    if not can_decide(role, action_type):
        raise ForbiddenError(
            f"'{role.value}' rolü '{action_type.value}' önerileri hakkında karar veremez"
        )


def payload_fingerprint(action_type: ActionType, order_id: str, payload: dict[str, Any]) -> str:
    """Stable hash of what was proposed. Any change afterwards needs a new proposal."""
    canonical = json.dumps(
        {"type": action_type.value, "order_id": order_id, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
