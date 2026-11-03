from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import User
from app.domain.enums import OrderStatus
from app.domain.errors import NotFoundError
from app.services.orders import OrderService
from app.services.policy import PolicyService
from tests.factories import make_customer, make_order

Headers = Callable[[User], dict[str, str]]


def test_missing_order_returns_404_and_never_invents_data(
    client: TestClient, agent: User, auth_headers: Headers
) -> None:
    response = client.get("/api/v1/orders/ORD-9999", headers=auth_headers(agent))
    assert response.status_code == 404
    assert response.json() == {"detail": "Sipariş bulunamadı: ORD-9999"}


def test_customer_orders_lists_only_that_customers_orders(
    client: TestClient, db_session: Session, agent: User, auth_headers: Headers
) -> None:
    alice, bob = make_customer(db_session, "CUS-A"), make_customer(db_session, "CUS-B")
    make_order(db_session, "ORD-A1", alice)
    make_order(db_session, "ORD-A2", alice, OrderStatus.SHIPPED)
    make_order(db_session, "ORD-B1", bob)

    response = client.get("/api/v1/customers/CUS-A/orders", headers=auth_headers(agent))

    assert response.status_code == 200
    assert {order["id"] for order in response.json()} == {"ORD-A1", "ORD-A2"}
    assert (
        client.get("/api/v1/customers/CUS-X/orders", headers=auth_headers(agent)).status_code == 404
    )


def test_scoped_lookup_treats_another_customers_order_as_missing(db_session: Session) -> None:
    alice, bob = make_customer(db_session, "CUS-A"), make_customer(db_session, "CUS-B")
    make_order(db_session, "ORD-B1", bob)
    orders = OrderService(db_session)

    with pytest.raises(NotFoundError) as foreign:
        orders.get_customer_order(alice.id, "ORD-B1")
    with pytest.raises(NotFoundError) as missing:
        orders.get_customer_order(alice.id, "ORD-NOPE")

    # Same error shape: the caller cannot tell "exists for someone else" from "missing".
    assert type(foreign.value) is type(missing.value)
    assert foreign.value.resource == missing.value.resource == "Order"


def test_policy_service_applies_rules_to_the_customers_order(db_session: Session) -> None:
    now = datetime(2026, 11, 2, tzinfo=UTC)
    customer = make_customer(db_session)
    make_order(db_session, "ORD-P1", customer, OrderStatus.PROCESSING)
    make_order(
        db_session, "ORD-D1", customer, OrderStatus.DELIVERED, delivered_at=now - timedelta(days=20)
    )
    policy = PolicyService(OrderService(db_session), clock=lambda: now)

    assert policy.address_change(customer.id, "ORD-P1").allowed
    assert not policy.address_change(customer.id, "ORD-D1").allowed
    assert not policy.return_request(customer.id, "ORD-D1").allowed  # 20 > 14 days
    assert policy.damage_report(customer.id, "ORD-D1").allowed  # 20 <= 30 days
