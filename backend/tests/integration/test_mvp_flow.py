"""The MVP exit criterion (ROADMAP Faz 5) as one end-to-end test through the API."""

from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Order, User
from app.domain.enums import OrderStatus
from app.services.proposals import ProposalService
from tests.factories import make_customer, make_order

Headers = Callable[[User], dict[str, str]]


def test_ticket_to_ai_proposal_to_approval_to_single_change(
    client: TestClient,
    db_session: Session,
    agent: User,
    admin: User,
    auth_headers: Headers,
) -> None:
    headers = auth_headers(agent)
    customer = make_customer(db_session, "CUS-A")
    make_order(db_session, "ORD-1003", customer, OrderStatus.PROCESSING)

    # 1. A request arrives through the API.
    ticket = client.post(
        "/api/v1/tickets",
        headers=headers,
        json={
            "customer_id": "CUS-A",
            "order_id": "ORD-1003",
            "subject": "Change delivery address",
            "message": "Please ship ORD-1003 to my new address: 42 Harbor St, Riverton.",
        },
    ).json()

    # 2. The AI gathers facts and proposes an action; the system stops there.
    run = client.post(f"/api/v1/tickets/{ticket['id']}/analyze", headers=headers).json()
    run = client.get(f"/api/v1/runs/{run['id']}", headers=headers).json()
    assert run["status"] == "succeeded"
    assert run["result"]["proposed_action"]["type"] == "change_shipping_address"
    assert db_session.get(Order, "ORD-1003").shipping_address == "1 Test St, Testville"  # type: ignore[union-attr]

    # 3. Pending work survives a restart (startup recovery leaves it alone).
    assert ProposalService(db_session).recover() == (0, 0)
    queue = client.get("/api/v1/proposals", headers=headers, params={"status": "pending"}).json()
    assert queue["total"] == 1
    proposal = queue["items"][0]
    assert proposal["can_decide"] is True

    # 4. An authorized employee approves; exactly one mock change happens.
    decided = client.post(
        f"/api/v1/proposals/{proposal['id']}/decision",
        headers=headers,
        json={"decision": "approve", "expected_version": proposal["version"]},
    ).json()
    assert decided["status"] == "executed"
    db_session.expire_all()
    assert db_session.get(Order, "ORD-1003").shipping_address == "42 Harbor St, Riverton"  # type: ignore[union-attr]

    # 5. Ticket history and audit trail tell the whole story.
    events = client.get(f"/api/v1/tickets/{ticket['id']}", headers=headers).json()["events"]
    assert [e["event_type"] for e in events] == [
        "ticket_created",
        "analysis_requested",
        "status_changed",
        "analysis_completed",
        "status_changed",
        "proposal_created",
        "proposal_approved",
        "action_executed",
    ]
    audit = client.get(
        "/api/v1/audit", headers=auth_headers(admin), params={"ticket_id": ticket["id"]}
    ).json()
    assert [entry["action"] for entry in audit] == [
        "proposal.created",
        "proposal.approved",
        "action.executed",
    ]
