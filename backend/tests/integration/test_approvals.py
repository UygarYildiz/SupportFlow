"""Phase 5: human approval and safe execution (ROADMAP Faz 5, TC-01..TC-05, TC-13, TC-19)."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.models import (
    ActionExecution,
    ActionProposal,
    AuditLog,
    Order,
    RefundRequest,
    Ticket,
    User,
)
from app.domain.enums import ActionType, OrderStatus, ProposalStatus, TicketStatus
from app.integrations.mock_orders import MockOrderSystem
from app.services.proposals import ProposalService
from tests.factories import make_customer, make_order, make_proposal, make_ticket

Headers = Callable[[User], dict[str, str]]
ORIGINAL_ADDRESS = "1 Test St, Testville"


@pytest.fixture
def order(db_session: Session) -> Order:
    return make_order(db_session, "ORD-A1", make_customer(db_session, "CUS-A"))


@pytest.fixture
def ticket(db_session: Session, order: Order) -> Ticket:
    customer = order.customer
    return make_ticket(db_session, customer, order=order, status=TicketStatus.AWAITING_REVIEW)


@pytest.fixture
def proposal(db_session: Session, ticket: Ticket, order: Order) -> ActionProposal:
    return make_proposal(db_session, ticket, order)


def _decide(
    client: TestClient,
    proposal_id: int,
    headers: dict[str, str],
    decision: str = "approve",
    version: int = 1,
):
    return client.post(
        f"/api/v1/proposals/{proposal_id}/decision",
        headers=headers,
        json={"decision": decision, "expected_version": version, "note": "checked"},
    )


def _executions(db_session: Session) -> int:
    return db_session.scalar(select(func.count(ActionExecution.id))) or 0


def test_proposal_alone_never_changes_anything(
    db_session: Session, proposal: ActionProposal, order: Order
) -> None:
    db_session.refresh(order)
    assert proposal.status == ProposalStatus.PENDING
    assert order.shipping_address == ORIGINAL_ADDRESS
    assert _executions(db_session) == 0


def test_approval_executes_the_change_exactly_once(
    client: TestClient,
    db_session: Session,
    proposal: ActionProposal,
    order: Order,
    agent: User,
    auth_headers: Headers,
) -> None:
    response = _decide(client, proposal.id, auth_headers(agent))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "executed"
    assert body["decided_by"] == agent.id
    assert body["version"] == 4  # pending -> approved -> executing -> executed
    db_session.refresh(order)
    assert order.shipping_address == "9 New Rd"
    assert _executions(db_session) == 1


def test_second_approval_is_rejected_and_changes_nothing(
    client: TestClient,
    db_session: Session,
    proposal: ActionProposal,
    order: Order,
    agent: User,
    admin: User,
    auth_headers: Headers,
) -> None:
    assert _decide(client, proposal.id, auth_headers(agent)).status_code == 200
    order.shipping_address = "changed by someone else later"
    db_session.commit()  # a separate, committed change (releases the test savepoint)

    # Double click (same version) and a second user (fresh version) both fail.
    stale = _decide(client, proposal.id, auth_headers(agent))
    late = _decide(client, proposal.id, auth_headers(admin), version=4)

    assert stale.status_code == 409
    assert late.status_code == 409
    assert "already 'executed'" in late.json()["detail"]
    db_session.refresh(order)
    assert order.shipping_address == "changed by someone else later"  # not re-applied
    assert _executions(db_session) == 1


def test_reject_ends_the_proposal_without_any_change(
    client: TestClient,
    db_session: Session,
    proposal: ActionProposal,
    order: Order,
    agent: User,
    auth_headers: Headers,
) -> None:
    response = _decide(client, proposal.id, auth_headers(agent), decision="reject")

    assert response.json()["status"] == "rejected"
    db_session.refresh(order)
    assert order.shipping_address == ORIGINAL_ADDRESS
    assert _executions(db_session) == 0
    # A rejected proposal cannot be approved afterwards.
    assert _decide(client, proposal.id, auth_headers(agent), version=2).status_code == 409


def test_agent_user_cannot_decide_a_refund_but_admin_can(
    client: TestClient,
    db_session: Session,
    ticket: Ticket,
    order: Order,
    agent: User,
    admin: User,
    auth_headers: Headers,
) -> None:
    order.status = OrderStatus.DELIVERED
    order.delivered_at = datetime.now(UTC) - timedelta(days=3)
    db_session.flush()
    refund = make_proposal(
        db_session,
        ticket,
        order,
        action_type=ActionType.CREATE_REFUND_REQUEST,
        payload={"refund_reason": "damaged_item", "order_total": "19.90 USD"},
        policy_rule="damaged_goods_v1",
    )

    forbidden = _decide(client, refund.id, auth_headers(agent))
    listed = client.get("/api/v1/proposals", headers=auth_headers(agent)).json()["items"][0]
    allowed = _decide(client, refund.id, auth_headers(admin))

    assert forbidden.status_code == 403
    assert listed["can_decide"] is False
    assert allowed.json()["status"] == "executed"
    refund_row = db_session.scalar(select(RefundRequest))
    assert refund_row is not None
    assert (refund_row.order_id, str(refund_row.amount)) == ("ORD-A1", "19.90")


def test_order_shipped_after_proposal_blocks_the_address_change(
    client: TestClient,
    db_session: Session,
    proposal: ActionProposal,
    order: Order,
    agent: User,
    auth_headers: Headers,
) -> None:
    order.status = OrderStatus.SHIPPED  # happens between proposal and approval
    db_session.flush()

    body = _decide(client, proposal.id, auth_headers(agent)).json()

    assert body["status"] == "failed"
    assert "only change before shipping" in body["failure_reason"]
    db_session.refresh(order)
    assert order.shipping_address == ORIGINAL_ADDRESS


def test_stale_version_is_rejected(
    client: TestClient, proposal: ActionProposal, agent: User, auth_headers: Headers
) -> None:
    response = _decide(client, proposal.id, auth_headers(agent), version=7)
    assert response.status_code == 409
    assert "reload before deciding" in response.json()["detail"]


def test_tampered_payload_cannot_be_executed(
    client: TestClient,
    db_session: Session,
    proposal: ActionProposal,
    order: Order,
    agent: User,
    auth_headers: Headers,
) -> None:
    db_session.execute(
        text("UPDATE action_proposals SET payload = :p WHERE id = :id"),
        {"p": '{"new_address": "attacker controlled"}', "id": proposal.id},
    )

    response = _decide(client, proposal.id, auth_headers(agent))

    assert response.status_code == 409
    assert "payload changed" in response.json()["detail"]
    db_session.refresh(order)
    assert order.shipping_address == ORIGINAL_ADDRESS


def test_expired_proposal_never_executes(
    client: TestClient,
    db_session: Session,
    ticket: Ticket,
    order: Order,
    agent: User,
    auth_headers: Headers,
) -> None:
    long_ago = datetime.now(UTC) - timedelta(days=5)
    stale = make_proposal(db_session, ticket, order, clock=lambda: long_ago, ttl_hours=48)

    response = _decide(client, stale.id, auth_headers(agent))

    assert response.status_code == 409
    db_session.refresh(stale)
    assert stale.status == ProposalStatus.EXPIRED
    db_session.refresh(order)
    assert order.shipping_address == ORIGINAL_ADDRESS


def test_execution_error_leaves_a_consistent_failed_state_and_audit(
    client: TestClient,
    db_session: Session,
    proposal: ActionProposal,
    order: Order,
    agent: User,
    auth_headers: Headers,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(self, request):
        raise RuntimeError("order system unavailable")

    monkeypatch.setattr(MockOrderSystem, "apply", boom)

    body = _decide(client, proposal.id, auth_headers(agent)).json()

    assert body["status"] == "failed"
    assert "nothing was changed" in body["failure_reason"]
    db_session.refresh(order)
    assert order.shipping_address == ORIGINAL_ADDRESS
    actions = list(db_session.scalars(select(AuditLog.action).order_by(AuditLog.id)))
    assert actions[-1] == "action.failed"


def test_restart_between_decision_and_execution_is_reconciled_once(
    db_session: Session, proposal: ActionProposal, order: Order
) -> None:
    # Simulate a crash right after step 1 (decision committed, nothing executed).
    proposal.status = ProposalStatus.EXECUTING
    db_session.flush()

    expired, reconciled = ProposalService(db_session).recover()
    again = ProposalService(db_session).recover()

    assert (expired, reconciled) == (0, 1)
    assert again == (0, 0)
    db_session.refresh(proposal)
    db_session.refresh(order)
    assert proposal.status == ProposalStatus.EXECUTED
    assert order.shipping_address == "9 New Rd"
    assert _executions(db_session) == 1


def test_idempotency_key_prevents_a_second_effect_even_if_called_again(
    db_session: Session, proposal: ActionProposal, order: Order
) -> None:
    from app.integrations.mock_orders import ActionRequest

    system = MockOrderSystem(db_session, clock=lambda: datetime.now(UTC))
    request = ActionRequest(
        proposal_id=proposal.id,
        action_type=proposal.type,
        customer_id=proposal.customer_id,
        order_id=proposal.order_id,
        payload=proposal.payload,
        policy_rule=proposal.policy_rule,
        idempotency_key=f"proposal-{proposal.id}",
        actor_id=None,
    )
    first = system.apply(request)
    order.shipping_address = "edited in between"
    db_session.flush()
    second = system.apply(request)

    assert not first.replayed
    assert second.replayed
    db_session.refresh(order)
    assert order.shipping_address == "edited in between"
    assert _executions(db_session) == 1


def test_one_open_proposal_per_ticket_and_new_analysis_supersedes(
    db_session: Session, ticket: Ticket, order: Order, proposal: ActionProposal
) -> None:
    newer = make_proposal(db_session, ticket, order, payload={"new_address": "7 Other Rd"})

    db_session.refresh(proposal)
    assert proposal.status == ProposalStatus.EXPIRED
    assert proposal.failure_reason is not None
    assert "Superseded" in proposal.failure_reason
    assert newer.status == ProposalStatus.PENDING


def test_audit_trail_is_redacted_admin_only_and_append_only(
    client: TestClient,
    db_session: Session,
    proposal: ActionProposal,
    ticket: Ticket,
    agent: User,
    admin: User,
    auth_headers: Headers,
) -> None:
    _decide(client, proposal.id, auth_headers(agent))

    assert client.get("/api/v1/audit", headers=auth_headers(agent)).status_code == 403
    entries = client.get(
        "/api/v1/audit", headers=auth_headers(admin), params={"ticket_id": ticket.id}
    ).json()
    assert [e["action"] for e in entries] == [
        "proposal.created",
        "proposal.approved",
        "action.executed",
    ]
    assert entries[1]["actor_id"] == agent.id
    assert "9 New Rd" not in str(entries)  # personal data redacted

    with pytest.raises(DBAPIError, match="append-only"):
        db_session.execute(text("UPDATE audit_logs SET action = 'tampered'"))


def test_agent_code_cannot_reach_the_executor() -> None:
    """Import boundary: nothing under app/agent may import execution or approval code."""
    agent_dir = Path(__file__).resolve().parents[2] / "app" / "agent"
    forbidden = ("app.integrations", "ProposalService", "MockOrderSystem", ".decide(")
    for source in agent_dir.rglob("*.py"):
        content = source.read_text(encoding="utf-8")
        for name in forbidden:
            assert name not in content, f"{source.name} references {name}"
