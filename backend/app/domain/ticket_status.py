"""Ticket lifecycle (ADR-008).

Two kinds of transitions exist:
- manual: performed by support staff through the API;
- system: performed only by the analysis pipeline (Phase 3+).
Keeping them apart means an employee cannot fake an AI triage step,
and the agent cannot resolve a ticket on its own.
"""

from app.domain.enums import TicketStatus
from app.domain.errors import InvalidStateTransitionError

S = TicketStatus

MANUAL_TRANSITIONS: dict[TicketStatus, frozenset[TicketStatus]] = {
    S.NEW: frozenset({S.RESOLVED, S.NEEDS_INFO}),
    S.AWAITING_REVIEW: frozenset({S.RESOLVED, S.NEEDS_INFO}),
    S.NEEDS_INFO: frozenset({S.NEW}),
    S.FAILED: frozenset({S.NEW}),
    S.TRIAGING: frozenset(),
    S.RESOLVED: frozenset(),
}

SYSTEM_TRANSITIONS: dict[TicketStatus, frozenset[TicketStatus]] = {
    S.NEW: frozenset({S.TRIAGING}),
    S.TRIAGING: frozenset({S.AWAITING_REVIEW, S.NEEDS_INFO, S.FAILED}),
}


def can_transition_manually(current: TicketStatus, target: TicketStatus) -> bool:
    return target in MANUAL_TRANSITIONS.get(current, frozenset())


def ensure_manual_transition(current: TicketStatus, target: TicketStatus) -> None:
    if not can_transition_manually(current, target):
        raise InvalidStateTransitionError("ticket", current.value, target.value)


def ensure_system_transition(current: TicketStatus, target: TicketStatus) -> None:
    if target not in SYSTEM_TRANSITIONS.get(current, frozenset()):
        raise InvalidStateTransitionError("ticket", current.value, target.value)
