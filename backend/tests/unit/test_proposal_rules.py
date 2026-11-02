import pytest

from app.domain.enums import ActionType, ProposalStatus, UserRole
from app.domain.errors import ForbiddenError, InvalidStateTransitionError
from app.domain.proposals import (
    TRANSITIONS,
    can_decide,
    ensure_can_decide,
    ensure_transition,
    payload_fingerprint,
)
from app.services.audit import REDACTED, redact

P = ProposalStatus


def test_refund_requests_need_an_admin() -> None:
    assert can_decide(UserRole.ADMIN, ActionType.CREATE_REFUND_REQUEST)
    assert not can_decide(UserRole.AGENT_USER, ActionType.CREATE_REFUND_REQUEST)
    with pytest.raises(ForbiddenError):
        ensure_can_decide(UserRole.AGENT_USER, ActionType.CREATE_REFUND_REQUEST)


def test_address_changes_can_be_decided_by_any_staff_role() -> None:
    for role in UserRole:
        ensure_can_decide(role, ActionType.CHANGE_SHIPPING_ADDRESS)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (P.PENDING, P.EXECUTING),  # no execution without an approval
        (P.REJECTED, P.APPROVED),  # decisions are final
        (P.EXPIRED, P.APPROVED),  # expired proposals never come back
        (P.EXECUTED, P.EXECUTING),  # never executed twice
    ],
)
def test_forbidden_proposal_transitions(current: ProposalStatus, target: ProposalStatus) -> None:
    with pytest.raises(InvalidStateTransitionError):
        ensure_transition(current, target)


def test_terminal_states_have_no_way_out() -> None:
    for status in (P.EXECUTED, P.REJECTED, P.FAILED, P.EXPIRED):
        assert TRANSITIONS[status] == frozenset()


def test_fingerprint_changes_with_any_part_of_the_proposal() -> None:
    base = payload_fingerprint(ActionType.CHANGE_SHIPPING_ADDRESS, "ORD-1", {"new_address": "A"})
    assert base == payload_fingerprint(
        ActionType.CHANGE_SHIPPING_ADDRESS, "ORD-1", {"new_address": "A"}
    )
    assert base != payload_fingerprint(
        ActionType.CHANGE_SHIPPING_ADDRESS, "ORD-1", {"new_address": "B"}
    )
    assert base != payload_fingerprint(
        ActionType.CHANGE_SHIPPING_ADDRESS, "ORD-2", {"new_address": "A"}
    )


def test_audit_details_redact_personal_data() -> None:
    details = {"order_id": "ORD-1", "payload": {"new_address": "9 New Rd", "refund_reason": "x"}}
    assert redact(details) == {
        "order_id": "ORD-1",
        "payload": {"new_address": REDACTED, "refund_reason": "x"},
    }
