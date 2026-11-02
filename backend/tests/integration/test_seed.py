from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Customer, Order, Ticket, TicketEvent, User
from app.demo.seed import TOTAL_ORDERS, TOTAL_TICKETS, seed_demo_data
from app.domain.enums import OrderStatus

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def _counts(session: Session) -> dict[str, int]:
    models = {"users": User, "customers": Customer, "orders": Order, "tickets": Ticket}
    counts = {
        name: session.scalar(select(func.count()).select_from(m)) or 0 for name, m in models.items()
    }
    counts["events"] = session.scalar(select(func.count()).select_from(TicketEvent)) or 0
    return counts


def test_seed_is_idempotent_and_matches_requirements(db_session: Session) -> None:
    first = seed_demo_data(db_session, NOW, "demo-pass")
    after_first = _counts(db_session)
    second = seed_demo_data(db_session, NOW, "demo-pass")

    assert (first.users, first.customers, first.orders, first.tickets) == (
        3,
        20,
        TOTAL_ORDERS,
        TOTAL_TICKETS,
    )
    assert (second.users, second.customers, second.orders, second.tickets) == (0, 0, 0, 0)
    assert _counts(db_session) == after_first


def test_seed_contains_the_scenario_edge_cases(db_session: Session) -> None:
    seed_demo_data(db_session, NOW, "demo-pass")

    assert db_session.get(Order, "ORD-1003").status == OrderStatus.PROCESSING  # type: ignore[union-attr]
    assert db_session.get(Order, "ORD-1004").status == OrderStatus.SHIPPED  # type: ignore[union-attr]
    # S4 edge case: ticket 6 asks about ORD-1003, which belongs to someone else.
    ticket_6 = db_session.get(Ticket, 6)
    order_1003 = db_session.get(Order, "ORD-1003")
    assert ticket_6 is not None
    assert order_1003 is not None
    assert ticket_6.customer_id != order_1003.customer_id
    assert "ORD-1003" in ticket_6.message


def test_new_tickets_after_seeding_do_not_collide_with_seeded_ids(db_session: Session) -> None:
    seed_demo_data(db_session, NOW, "demo-pass")
    ticket = Ticket(customer_id="CUS-0001", subject="New", message="After seed")
    db_session.add(ticket)
    db_session.flush()
    assert ticket.id > TOTAL_TICKETS


def test_scenario_orders_contain_the_products_their_tickets_mention(db_session: Session) -> None:
    seed_demo_data(db_session, NOW, "demo-pass")
    expected = {"ORD-1001": "Headphones", "ORD-1002": "Kettle", "ORD-1005": "Yoga Mat",
                "ORD-1006": "Speaker", "ORD-1007": "Pan", "ORD-1009": "Mug Set"}  # fmt: skip
    for order_id, product in expected.items():
        order = db_session.get(Order, order_id)
        assert order is not None
        assert any(product in item["name"] for item in order.items), order_id
