"""The read-only MCP server (Phase 8, ADR-015): scope, identity, errors and audit."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.mcp_tools import error_code
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.models import AuditLog, Ticket, User
from app.domain.enums import OrderStatus, UserRole
from app.mcp.access import agent_run_authenticator, staff_token_authenticator
from app.mcp.server import AUDIT_ACTION, build_server
from app.services.support_lookup import SupportLookupService
from tests.factories import make_customer, make_order, make_ticket, make_user
from tests.mcp_client import call_tool, error_text


@pytest.fixture
def scope(db_session: Session):
    @contextmanager
    def session_scope() -> Iterator[Session]:
        yield db_session

    return session_scope


@pytest.fixture
def staff(db_session: Session) -> User:
    return make_user(db_session, "mcp-agent@test.example", UserRole.AGENT_USER)


@pytest.fixture
def ticket(db_session: Session) -> Ticket:
    """CUS-A's ticket about ORD-A1; CUS-B owns ORD-B1."""
    customer = make_customer(db_session, "CUS-A")
    order = make_order(db_session, "ORD-A1", customer, OrderStatus.SHIPPED)
    make_order(db_session, "ORD-B1", make_customer(db_session, "CUS-B"))
    return make_ticket(db_session, customer, order=order, subject="Where is my order?")


def _staff_server(scope, user: User, *, token: str | None = None):
    settings = get_settings()
    token = token or create_access_token(user.id, user.role, settings)
    return build_server(
        session_scope=scope, authenticate=staff_token_authenticator(SecretStr(token), settings)
    )


def _audits(db_session: Session) -> list[AuditLog]:
    return list(db_session.scalars(select(AuditLog).where(AuditLog.action == AUDIT_ACTION)))


def test_staff_reads_an_order_of_the_ticket_customer(scope, staff: User, ticket: Ticket) -> None:
    result = call_tool(
        _staff_server(scope, staff),
        "get_order_status",
        {"ticket_id": ticket.id, "order_id": "ORD-A1"},
    )

    assert not result.is_error
    data = result.structured_content
    assert data is not None
    assert (data["id"], data["status"]) == ("ORD-A1", "shipped")
    assert data["items"] == [{"name": "Test item", "quantity": 1}]
    assert "sku" not in str(data)  # only the declared fields leave the server


def test_tc14_another_customers_order_is_not_found_without_leaking_data(
    scope, staff: User, ticket: Ticket
) -> None:
    """TC-14: an order of another customer looks exactly like a missing one."""
    server = _staff_server(scope, staff)

    foreign = call_tool(server, "get_order_status", {"ticket_id": ticket.id, "order_id": "ORD-B1"})
    missing = call_tool(server, "get_order_status", {"ticket_id": ticket.id, "order_id": "ORD-X9"})

    assert error_code(foreign) == error_code(missing) == "not_found"
    assert error_text(foreign).replace("ORD-B1", "ORD-X9") == error_text(missing)
    assert foreign.structured_content is None
    assert "CUS-B" not in error_text(foreign)
    assert "Test St" not in error_text(foreign)


def test_lists_are_scoped_to_the_tickets_customer(
    db_session: Session, scope, staff: User, ticket: Ticket
) -> None:
    customer_a = ticket.customer_id
    older = make_ticket(db_session, ticket.customer, subject="Earlier question")
    make_ticket(db_session, make_customer(db_session, "CUS-C"), subject="Someone else")
    assert customer_a == "CUS-A"
    server = _staff_server(scope, staff)

    orders = call_tool(server, "get_customer_orders", {"ticket_id": ticket.id})
    history = call_tool(server, "get_ticket_history", {"ticket_id": ticket.id})

    assert orders.structured_content is not None
    assert [o["id"] for o in orders.structured_content["orders"]] == ["ORD-A1"]
    assert history.structured_content is not None
    assert [t["id"] for t in history.structured_content["tickets"]] == [older.id]


def test_an_unknown_ticket_is_not_found(scope, staff: User) -> None:
    result = call_tool(_staff_server(scope, staff), "get_customer_orders", {"ticket_id": 999_999})

    assert error_code(result) == "not_found"


def test_an_analysis_connection_reads_only_its_own_ticket(
    db_session: Session, scope, ticket: Ticket
) -> None:
    other = make_ticket(db_session, make_customer(db_session, "CUS-D"))
    server = build_server(
        session_scope=scope,
        authenticate=agent_run_authenticator(ticket.id, run_id=7),
        audit_calls=False,
    )

    own = call_tool(server, "get_customer_orders", {"ticket_id": ticket.id})
    foreign = call_tool(server, "get_customer_orders", {"ticket_id": other.id})

    assert not own.is_error
    assert error_code(foreign) == "forbidden"
    assert foreign.structured_content is None


@pytest.mark.parametrize("problem", ["expired", "garbage", "deactivated"])
def test_identity_comes_from_a_valid_staff_token_only(
    db_session: Session, scope, staff: User, ticket: Ticket, problem: str
) -> None:
    settings = get_settings()
    token: str | None = None
    if problem == "expired":
        token = create_access_token(
            staff.id, staff.role, settings, now=datetime.now(UTC) - timedelta(days=1)
        )
    elif problem == "garbage":
        token = "not-a-token"
    else:  # a valid token of a user deactivated since: refused on the next call
        staff.is_active = False
        db_session.flush()

    result = call_tool(
        _staff_server(scope, staff, token=token),
        "get_order_status",
        {"ticket_id": ticket.id, "order_id": "ORD-A1"},
    )

    assert error_code(result) == "unauthorized"
    assert result.structured_content is None


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("get_order_status", {"ticket_id": 1, "order_id": "../../etc"}),
        ("get_order_status", {"ticket_id": 0, "order_id": "ORD-A1"}),
        ("get_order_status", {"ticket_id": 1}),
        ("get_customer_orders", {"ticket_id": 1, "limit": 1000}),
        ("get_ticket_history", {"ticket_id": "1; DROP TABLE tickets"}),
    ],
)
def test_arguments_are_validated_before_anything_runs(
    scope, staff: User, tool: str, arguments: dict
) -> None:
    result = call_tool(_staff_server(scope, staff), tool, arguments)

    assert error_code(result) == "invalid_arguments"


def test_staff_calls_are_audited_and_logged_with_a_call_id(
    db_session: Session,
    scope,
    staff: User,
    ticket: Ticket,
    caplog: pytest.LogCaptureFixture,
) -> None:
    server = _staff_server(scope, staff)
    with caplog.at_level(logging.INFO, logger="app.mcp.server"):
        call_tool(server, "get_order_status", {"ticket_id": ticket.id, "order_id": "ORD-A1"})
        call_tool(server, "get_order_status", {"ticket_id": ticket.id, "order_id": "ORD-B1"})

    entries = _audits(db_session)
    assert [(e.actor_id, e.ticket_id, e.details["outcome"]) for e in entries] == [
        (staff.id, ticket.id, "ok"),
        (staff.id, ticket.id, "not_found"),
    ]
    assert entries[0].resource_id == "get_order_status"
    call_ids = [e.details["call_id"] for e in entries]
    assert len(set(call_ids)) == 2
    for call_id, outcome in zip(call_ids, ["ok", "not_found"], strict=True):
        line = next(r.getMessage() for r in caplog.records if call_id in r.getMessage())
        assert f"outcome={outcome}" in line
        assert f"caller=user:{staff.id}" in line
    assert "Test St" not in caplog.text  # no customer data in the logs


def test_analysis_calls_are_logged_but_not_audited(
    db_session: Session, scope, ticket: Ticket, caplog: pytest.LogCaptureFixture
) -> None:
    server = build_server(
        session_scope=scope, authenticate=agent_run_authenticator(ticket.id, 3), audit_calls=False
    )
    with caplog.at_level(logging.INFO, logger="app.mcp.server"):
        call_tool(server, "get_customer_orders", {"ticket_id": ticket.id})

    assert _audits(db_session) == []  # run steps record these calls
    assert "caller=run:3" in caplog.text


def test_an_unexpected_failure_reveals_nothing(
    monkeypatch: pytest.MonkeyPatch,
    scope,
    staff: User,
    ticket: Ticket,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def crash(*_args: object) -> None:
        raise RuntimeError("connection string postgres://secret@db")

    monkeypatch.setattr(SupportLookupService, "order_for_ticket", crash)

    with caplog.at_level(logging.ERROR, logger="app.mcp.server"):
        result = call_tool(
            _staff_server(scope, staff),
            "get_order_status",
            {"ticket_id": ticket.id, "order_id": "ORD-A1"},
        )

    assert error_code(result) == "internal_error"
    assert "secret" not in error_text(result)
    assert "crashed" in caplog.text  # the details stay in the server log
