"""First-run setup of a self-hosted installation (ADR-017, SECURITY T21)."""

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import AuditLog, Installation, User
from tests.factories import make_user

SETUP_TOKEN = "setup-code-0123456789"
PASSWORD = "uzun ve güçlü bir parola"


def _setup_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "organization_name": "Kuzey Kırtasiye",
        "full_name": "Deniz Kaya",
        "email": "Deniz@KuzeyKirtasiye.example",
        "password": PASSWORD,
        "setup_token": SETUP_TOKEN,
    }
    body.update(overrides)
    return body


def _user_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(User)) or 0


@pytest.fixture
def use_settings(app: FastAPI) -> Callable[..., None]:
    def apply(**values: object) -> None:
        settings = Settings(**values)  # type: ignore[arg-type]
        app.dependency_overrides[get_settings] = lambda: settings

    return apply


@pytest.fixture
def self_hosted(use_settings: Callable[..., None]) -> None:
    use_settings(deployment_mode="self_hosted", setup_token=SecretStr(SETUP_TOKEN))


def test_a_demo_installation_never_offers_setup(
    client: TestClient, db_session: Session, use_settings: Callable[..., None]
) -> None:
    use_settings(deployment_mode="demo")
    status = client.get("/api/v1/setup/status").json()
    assert status["mode"] == "demo"
    assert status["setup_required"] is False

    response = client.post("/api/v1/setup", json=_setup_body())
    assert response.status_code == 409
    assert _user_count(db_session) == 0


@pytest.mark.usefixtures("self_hosted")
def test_first_run_setup_creates_the_business_and_signs_in_its_admin(
    client: TestClient, db_session: Session
) -> None:
    before = client.get("/api/v1/setup/status").json()
    assert before == {
        "mode": "self_hosted",
        "setup_required": True,
        "setup_token_required": True,
        "organization_name": None,
    }

    response = client.post("/api/v1/setup", json=_setup_body())
    assert response.status_code == 201
    token = response.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["role"] == "admin"
    assert me["email"] == "deniz@kuzeykirtasiye.example"  # stored in canonical form

    after = client.get("/api/v1/setup/status").json()
    assert after["setup_required"] is False
    assert after["organization_name"] == "Kuzey Kırtasiye"

    audit = db_session.scalar(select(AuditLog).where(AuditLog.action == "setup.completed"))
    assert audit is not None
    assert audit.actor_id == me["id"]

    # The same credentials work through the normal login.
    login = client.post(
        "/api/v1/auth/login", json={"email": "deniz@kuzeykirtasiye.example", "password": PASSWORD}
    )
    assert login.status_code == 200


@pytest.mark.usefixtures("self_hosted")
def test_setup_works_exactly_once(client: TestClient, db_session: Session) -> None:
    assert client.post("/api/v1/setup", json=_setup_body()).status_code == 201

    second = client.post(
        "/api/v1/setup", json=_setup_body(email="saldirgan@example.com", setup_token="wrong")
    )
    # A finished installation says only that; it does not even check the code.
    assert second.status_code == 409
    assert second.json() == {"detail": "Kurulum zaten tamamlanmış. Giriş yapın."}
    assert _user_count(db_session) == 1


@pytest.mark.usefixtures("self_hosted")
def test_setup_needs_the_setup_code(client: TestClient, db_session: Session) -> None:
    for token in (None, "", "wrong-code-0123456789"):
        response = client.post("/api/v1/setup", json=_setup_body(setup_token=token))
        assert response.status_code == 403
        assert response.json() == {"detail": "Kurulum kodu hatalı"}
    assert _user_count(db_session) == 0
    assert client.get("/api/v1/setup/status").json()["setup_required"] is True


def test_without_a_configured_code_setup_does_not_ask_for_one(
    client: TestClient, db_session: Session, use_settings: Callable[..., None]
) -> None:
    use_settings(deployment_mode="self_hosted")  # development: no SETUP_TOKEN
    assert client.get("/api/v1/setup/status").json()["setup_token_required"] is False
    response = client.post("/api/v1/setup", json=_setup_body(setup_token=None))
    assert response.status_code == 201


@pytest.mark.usefixtures("self_hosted")
def test_an_invalid_setup_creates_nothing(client: TestClient, db_session: Session) -> None:
    weak = client.post("/api/v1/setup", json=_setup_body(password="kisa"))
    assert weak.status_code == 422
    assert "en az" in weak.json()["detail"]

    blank = client.post("/api/v1/setup", json=_setup_body(organization_name="   "))
    assert blank.status_code == 422

    assert _user_count(db_session) == 0
    assert db_session.get(Installation, 1) is None


@pytest.mark.usefixtures("self_hosted")
def test_a_database_with_accounts_is_never_offered_setup(
    client: TestClient, db_session: Session
) -> None:
    make_user(db_session, "existing@example.com")
    assert client.get("/api/v1/setup/status").json()["setup_required"] is False
    assert client.post("/api/v1/setup", json=_setup_body()).status_code == 409


def test_the_database_allows_a_single_installation_record(db_session: Session) -> None:
    admin = make_user(db_session, "first@example.com")
    db_session.add(Installation(id=1, organization_name="A", completed_by_id=admin.id))
    db_session.flush()

    for row_id in (1, 2):  # 1: duplicate primary key; 2: violates the single-row check
        with pytest.raises(IntegrityError), db_session.begin_nested():
            db_session.execute(
                text(
                    "INSERT INTO installation (id, organization_name, completed_by_id, "
                    "completed_at) VALUES (:id, 'B', :user, now())"
                ),
                {"id": row_id, "user": admin.id},
            )
