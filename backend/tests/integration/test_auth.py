from collections.abc import Callable

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import User
from app.domain.enums import UserRole
from tests.factories import TEST_PASSWORD, make_user


def test_login_returns_token_that_authenticates_the_user(client: TestClient, agent: User) -> None:
    response = client.post(
        "/api/v1/auth/login", json={"email": "AGENT@test.example", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == agent.email
    assert me.json()["role"] == "agent_user"
    assert "password_hash" not in me.text


def test_login_failures_are_indistinguishable(client: TestClient, db_session: Session) -> None:
    make_user(db_session, "inactive@test.example", is_active=False)
    make_user(db_session, "active@test.example")

    attempts = [
        ("nobody@test.example", TEST_PASSWORD),  # unknown account
        ("active@test.example", "wrong-password"),  # wrong password
        ("inactive@test.example", TEST_PASSWORD),  # deactivated account
    ]
    for email, password in attempts:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 401
        assert response.json() == {"detail": "E-posta ya da parola hatalı"}


def test_requests_without_valid_token_get_401(client: TestClient, db_session: Session) -> None:
    for headers in ({}, {"Authorization": "Bearer not-a-jwt"}):
        response = client.get("/api/v1/tickets", headers=headers)
        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"


def test_deactivated_user_loses_access_immediately(
    client: TestClient,
    db_session: Session,
    agent: User,
    auth_headers: Callable[[User], dict[str, str]],
) -> None:
    headers = auth_headers(agent)
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    agent.is_active = False
    db_session.flush()

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_admin_only_endpoint_rejects_agent_users(
    client: TestClient, admin: User, agent: User, auth_headers: Callable[[User], dict[str, str]]
) -> None:
    assert client.get("/api/v1/users", headers=auth_headers(agent)).status_code == 403

    response = client.get("/api/v1/users", headers=auth_headers(admin))
    assert response.status_code == 200
    roles = {user["email"]: user["role"] for user in response.json()}
    assert roles == {admin.email: UserRole.ADMIN.value, agent.email: UserRole.AGENT_USER.value}
