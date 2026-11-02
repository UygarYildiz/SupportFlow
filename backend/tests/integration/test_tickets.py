from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Ticket, TicketEvent, User
from app.domain.enums import TicketPriority, TicketStatus
from tests.factories import make_customer, make_order, make_ticket

Headers = Callable[[User], dict[str, str]]


def test_create_ticket_records_creation_event(
    client: TestClient, db_session: Session, agent: User, auth_headers: Headers
) -> None:
    customer = make_customer(db_session)
    make_order(db_session, "ORD-1", customer)

    response = client.post(
        "/api/v1/tickets",
        headers=auth_headers(agent),
        json={
            "customer_id": customer.id,
            "order_id": "ORD-1",
            "subject": "Where is my order?",
            "message": "It has not arrived yet.",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "new"
    assert body["priority"] == "medium"
    assert body["order"]["id"] == "ORD-1"
    assert body["customer"]["id"] == customer.id
    assert [(e["event_type"], e["actor_type"], e["actor_id"]) for e in body["events"]] == [
        ("ticket_created", "user", agent.id)
    ]


def test_ticket_cannot_reference_another_customers_order(
    client: TestClient, db_session: Session, agent: User, auth_headers: Headers
) -> None:
    alice, bob = make_customer(db_session, "CUS-A"), make_customer(db_session, "CUS-B")
    make_order(db_session, "ORD-B1", bob)
    payload = {"customer_id": alice.id, "subject": "Status", "message": "Where is it?"}

    foreign = client.post(
        "/api/v1/tickets", headers=auth_headers(agent), json={**payload, "order_id": "ORD-B1"}
    )
    missing = client.post(
        "/api/v1/tickets", headers=auth_headers(agent), json={**payload, "order_id": "ORD-X"}
    )

    assert foreign.status_code == missing.status_code == 422
    # The message does not reveal that ORD-B1 exists for another customer.
    assert "does not match any order of this customer" in foreign.json()["detail"]
    assert db_session.scalar(select(func.count(Ticket.id))) == 0


def test_database_also_enforces_order_ownership(db_session: Session) -> None:
    """Second line of defence: the composite foreign key rejects a mismatched order."""
    alice, bob = make_customer(db_session, "CUS-A"), make_customer(db_session, "CUS-B")
    bobs_order = make_order(db_session, "ORD-B1", bob)

    with pytest.raises(IntegrityError):
        make_ticket(db_session, alice, order=bobs_order)


def test_unknown_ticket_returns_404(client: TestClient, agent: User, auth_headers: Headers) -> None:
    assert client.get("/api/v1/tickets/999999", headers=auth_headers(agent)).status_code == 404


def test_valid_status_change_is_recorded_in_history(
    client: TestClient, db_session: Session, agent: User, auth_headers: Headers
) -> None:
    ticket = make_ticket(db_session, make_customer(db_session))

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}",
        headers=auth_headers(agent),
        json={"status": "resolved", "priority": "high"},
    )

    assert response.status_code == 200
    body = response.json()
    assert (body["status"], body["priority"]) == ("resolved", "high")
    changes = [(e["event_type"], e["payload"]) for e in body["events"]]
    assert ("status_changed", {"from": "new", "to": "resolved"}) in changes
    assert ("priority_changed", {"from": "medium", "to": "high"}) in changes


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (TicketStatus.RESOLVED, "new"),
        (TicketStatus.NEW, "triaging"),  # reserved for the analysis pipeline
        (TicketStatus.NEW, "awaiting_review"),
    ],
)
def test_invalid_status_change_returns_409_and_changes_nothing(
    client: TestClient,
    db_session: Session,
    agent: User,
    auth_headers: Headers,
    current: TicketStatus,
    target: str,
) -> None:
    ticket = make_ticket(db_session, make_customer(db_session), status=current)

    response = client.patch(
        f"/api/v1/tickets/{ticket.id}", headers=auth_headers(agent), json={"status": target}
    )

    assert response.status_code == 409
    db_session.refresh(ticket)
    assert ticket.status == current
    assert db_session.scalar(select(func.count(TicketEvent.id))) == 0


def test_patch_rejects_empty_body_and_immutable_fields(
    client: TestClient, db_session: Session, agent: User, auth_headers: Headers
) -> None:
    ticket = make_ticket(db_session, make_customer(db_session))
    url = f"/api/v1/tickets/{ticket.id}"

    assert client.patch(url, headers=auth_headers(agent), json={}).status_code == 422
    # Customer-written content cannot be edited; unknown fields are ignored.
    response = client.patch(
        url, headers=auth_headers(agent), json={"message": "edited", "priority": "low"}
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Test message"


def test_list_filters_and_paginates(
    client: TestClient, db_session: Session, agent: User, auth_headers: Headers
) -> None:
    customer = make_customer(db_session)
    for _ in range(3):
        make_ticket(db_session, customer, priority=TicketPriority.HIGH)
    make_ticket(db_session, customer, status=TicketStatus.RESOLVED)

    first_page = client.get(
        "/api/v1/tickets",
        headers=auth_headers(agent),
        params={"status": "new", "priority": "high", "limit": 2},
    ).json()
    second_page = client.get(
        "/api/v1/tickets",
        headers=auth_headers(agent),
        params={"status": "new", "priority": "high", "limit": 2, "offset": 2},
    ).json()

    assert first_page["total"] == second_page["total"] == 3
    assert len(first_page["items"]) == 2
    assert len(second_page["items"]) == 1
    ids = {t["id"] for t in first_page["items"]} | {t["id"] for t in second_page["items"]}
    assert len(ids) == 3
    assert "message" not in first_page["items"][0]  # list view stays lightweight
