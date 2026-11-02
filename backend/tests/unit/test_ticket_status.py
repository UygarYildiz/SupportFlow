import pytest

from app.domain.enums import TicketStatus as S
from app.domain.errors import InvalidStateTransitionError
from app.domain.ticket_status import (
    MANUAL_TRANSITIONS,
    can_transition_manually,
    ensure_manual_transition,
    ensure_system_transition,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.NEW, S.RESOLVED),
        (S.NEW, S.NEEDS_INFO),
        (S.AWAITING_REVIEW, S.RESOLVED),
        (S.AWAITING_REVIEW, S.NEEDS_INFO),
        (S.NEEDS_INFO, S.NEW),
        (S.FAILED, S.NEW),
    ],
)
def test_staff_can_make_allowed_manual_transitions(current: S, target: S) -> None:
    ensure_manual_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (S.RESOLVED, S.NEW),  # resolved is terminal
        (S.NEW, S.AWAITING_REVIEW),  # skipping AI triage
        (S.TRIAGING, S.RESOLVED),  # interfering with a running analysis
    ],
)
def test_invalid_manual_transition_is_rejected(current: S, target: S) -> None:
    with pytest.raises(InvalidStateTransitionError) as error:
        ensure_manual_transition(current, target)
    assert error.value.current == current.value
    assert error.value.target == target.value


def test_triage_states_are_reserved_for_the_system() -> None:
    # Staff cannot fake an AI triage step ...
    assert not can_transition_manually(S.NEW, S.TRIAGING)
    assert not can_transition_manually(S.TRIAGING, S.AWAITING_REVIEW)
    # ... and the system cannot resolve a ticket on its own.
    ensure_system_transition(S.NEW, S.TRIAGING)
    ensure_system_transition(S.TRIAGING, S.AWAITING_REVIEW)
    with pytest.raises(InvalidStateTransitionError):
        ensure_system_transition(S.AWAITING_REVIEW, S.RESOLVED)


def test_every_status_has_a_manual_transition_rule() -> None:
    assert set(MANUAL_TRANSITIONS) == set(S)
