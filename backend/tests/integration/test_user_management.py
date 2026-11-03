"""Admins manage their own staff accounts (ADR-017, SECURITY T22)."""

from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditLog, User
from app.domain.enums import UserRole
from app.domain.errors import BusinessRuleViolationError
from app.services.users import UserService
from tests.factories import TEST_PASSWORD, make_user

NEW_PASSWORD = "ilk giriş parolası 2026"

Headers = Callable[[User], dict[str, str]]


def _login(client: TestClient, email: str, password: str) -> int:
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    ).status_code


def test_admin_adds_a_staff_member_who_can_sign_in(
    client: TestClient, db_session: Session, admin: User, auth_headers: Headers
) -> None:
    response = client.post(
        "/api/v1/users",
        headers=auth_headers(admin),
        json={"email": " Ece@Isletme.Example", "full_name": "Ece Koç", "password": NEW_PASSWORD},
    )
    assert response.status_code == 201
    created = response.json()
    assert created["email"] == "ece@isletme.example"
    assert created["role"] == "agent_user"  # the default: least privilege
    assert "password" not in response.text

    assert _login(client, "ECE@isletme.example", NEW_PASSWORD) == 200

    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "user.created"))
    assert audit is not None
    assert audit.actor_id == admin.id
    assert NEW_PASSWORD not in str(audit.details)


def test_an_address_can_belong_to_one_account_only(
    client: TestClient, admin: User, agent: User, auth_headers: Headers
) -> None:
    response = client.post(
        "/api/v1/users",
        headers=auth_headers(admin),
        json={"email": agent.email.upper(), "full_name": "Kopya", "password": NEW_PASSWORD},
    )
    assert response.status_code == 409
    assert response.json() == {"detail": "Bu e-posta adresiyle bir hesap zaten var"}


def test_only_admins_manage_accounts(
    client: TestClient, admin: User, agent: User, auth_headers: Headers
) -> None:
    headers = auth_headers(agent)
    body = {"email": "x@isletme.example", "full_name": "X", "password": NEW_PASSWORD}
    assert client.post("/api/v1/users", headers=headers, json=body).status_code == 403
    patch = client.patch(f"/api/v1/users/{admin.id}", headers=headers, json={"is_active": False})
    assert patch.status_code == 403
    assert client.post("/api/v1/users", json=body).status_code == 401


def test_weak_initial_passwords_are_refused(
    client: TestClient, admin: User, auth_headers: Headers
) -> None:
    response = client.post(
        "/api/v1/users",
        headers=auth_headers(admin),
        json={"email": "zayif@isletme.example", "full_name": "Zayıf", "password": "123456"},
    )
    assert response.status_code == 422
    assert _login(client, "zayif@isletme.example", "123456") == 401


def test_a_deactivated_member_loses_access_and_can_be_restored(
    client: TestClient, db_session: Session, admin: User, agent: User, auth_headers: Headers
) -> None:
    agent_headers = auth_headers(agent)
    off = client.patch(
        f"/api/v1/users/{agent.id}", headers=auth_headers(admin), json={"is_active": False}
    )
    assert off.status_code == 200
    assert off.json()["is_active"] is False
    assert client.get("/api/v1/auth/me", headers=agent_headers).status_code == 401
    assert _login(client, agent.email, TEST_PASSWORD) == 401

    on = client.patch(
        f"/api/v1/users/{agent.id}", headers=auth_headers(admin), json={"is_active": True}
    )
    assert on.status_code == 200
    assert client.get("/api/v1/auth/me", headers=agent_headers).status_code == 200


def test_role_changes_take_effect_on_the_next_request(
    client: TestClient, admin: User, agent: User, auth_headers: Headers
) -> None:
    agent_headers = auth_headers(agent)
    assert client.get("/api/v1/users", headers=agent_headers).status_code == 403

    promoted = client.patch(
        f"/api/v1/users/{agent.id}", headers=auth_headers(admin), json={"role": "admin"}
    )
    assert promoted.json()["role"] == "admin"
    # Same token: the role is re-read from the database (ADR-007).
    assert client.get("/api/v1/users", headers=agent_headers).status_code == 200


def test_admins_cannot_lock_themselves_out(
    client: TestClient, db_session: Session, admin: User, auth_headers: Headers
) -> None:
    db_session.commit()  # the 422 path rolls back; keep the fixture user
    headers = auth_headers(admin)
    for change in ({"is_active": False}, {"role": "agent_user"}):
        response = client.patch(f"/api/v1/users/{admin.id}", headers=headers, json=change)
        assert response.status_code == 422
    assert client.get("/api/v1/auth/me", headers=headers).json()["role"] == "admin"

    # Their own name and password are fine.
    renamed = client.patch(
        f"/api/v1/users/{admin.id}", headers=headers, json={"full_name": "Ayşe D."}
    )
    assert renamed.json()["full_name"] == "Ayşe D."


def test_two_admins_demoting_each_other_leave_one_admin(db_session: Session) -> None:
    """Both requests passed authentication while both were admins; the second must fail."""
    first = make_user(db_session, "a@isletme.example", UserRole.ADMIN)
    second = make_user(db_session, "b@isletme.example", UserRole.ADMIN)
    db_session.commit()
    users = UserService(db_session)

    users.update(second.id, actor=first, role=UserRole.AGENT_USER)
    with pytest.raises(BusinessRuleViolationError, match="yönetici"):
        users.update(first.id, actor=second, role=UserRole.AGENT_USER)

    db_session.refresh(first)
    assert first.role == UserRole.ADMIN


def test_admin_resets_a_forgotten_password(
    client: TestClient, admin: User, agent: User, auth_headers: Headers
) -> None:
    response = client.patch(
        f"/api/v1/users/{agent.id}", headers=auth_headers(admin), json={"password": NEW_PASSWORD}
    )
    assert response.status_code == 200
    assert _login(client, agent.email, NEW_PASSWORD) == 200
    assert _login(client, agent.email, TEST_PASSWORD) == 401


def test_unknown_account_is_404(client: TestClient, admin: User, auth_headers: Headers) -> None:
    response = client.patch(
        "/api/v1/users/99999", headers=auth_headers(admin), json={"is_active": False}
    )
    assert response.status_code == 404


def test_staff_change_their_own_password(
    client: TestClient, db_session: Session, agent: User, auth_headers: Headers
) -> None:
    db_session.commit()
    headers = auth_headers(agent)
    wrong = client.post(
        "/api/v1/auth/password",
        headers=headers,
        json={"current_password": "not-my-password", "new_password": NEW_PASSWORD},
    )
    assert wrong.status_code == 422
    assert wrong.json() == {"detail": "Mevcut parola hatalı"}

    ok = client.post(
        "/api/v1/auth/password",
        headers=headers,
        json={"current_password": TEST_PASSWORD, "new_password": NEW_PASSWORD},
    )
    assert ok.status_code == 200
    assert _login(client, agent.email, NEW_PASSWORD) == 200
    assert _login(client, agent.email, TEST_PASSWORD) == 401

    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "user.password_changed"))
    assert audit is not None
