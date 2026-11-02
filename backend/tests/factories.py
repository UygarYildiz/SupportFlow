"""Minimal builders for test data. Each test creates only what it needs."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import Customer, Order, Ticket, User
from app.domain.enums import OrderStatus, TicketPriority, TicketStatus, UserRole

TEST_PASSWORD = "correct-horse-battery"
# Hashing is deliberately slow (Argon2); compute once for all test users.
_TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


def make_user(
    session: Session, email: str, role: UserRole = UserRole.AGENT_USER, *, is_active: bool = True
) -> User:
    user = User(
        email=email,
        full_name=email.split("@")[0].title(),
        role=role,
        password_hash=_TEST_PASSWORD_HASH,
        is_active=is_active,
    )
    session.add(user)
    session.flush()
    return user


def make_customer(session: Session, customer_id: str = "CUS-T001") -> Customer:
    customer = Customer(
        id=customer_id,
        display_name=f"Customer {customer_id}",
        email=f"{customer_id.lower()}@example.com",
    )
    session.add(customer)
    session.flush()
    return customer


def make_order(
    session: Session,
    order_id: str,
    customer: Customer,
    status: OrderStatus = OrderStatus.PROCESSING,
    *,
    delivered_at: datetime | None = None,
) -> Order:
    order = Order(
        id=order_id,
        customer_id=customer.id,
        status=status,
        total_amount=Decimal("19.90"),
        currency="USD",
        shipping_address="1 Test St, Testville",
        items=[{"sku": "T-1", "name": "Test item", "quantity": 1, "unit_price": "19.90"}],
        created_at=datetime(2026, 10, 1, tzinfo=UTC),
        delivered_at=delivered_at,
    )
    session.add(order)
    session.flush()
    return order


def make_ticket(
    session: Session,
    customer: Customer,
    *,
    order: Order | None = None,
    status: TicketStatus = TicketStatus.NEW,
    priority: TicketPriority = TicketPriority.MEDIUM,
    subject: str = "Test ticket",
) -> Ticket:
    ticket = Ticket(
        customer_id=customer.id,
        order_id=order.id if order else None,
        subject=subject,
        message="Test message",
        status=status,
        priority=priority,
    )
    session.add(ticket)
    session.flush()
    return ticket
