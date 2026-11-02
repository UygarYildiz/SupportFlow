"""Shared test fixtures.

Tests that use `db_session` (directly or through `client`) need the Postgres
test database from compose.yaml (`docker compose up -d db`). Its URL comes from
TEST_DATABASE_URL (environment or repo-root .env).

Isolation: each test runs inside an outer transaction that is rolled back at
the end. Service code may call `commit()`; with `join_transaction_mode=
"create_savepoint"` that only releases a savepoint, so nothing leaks between tests.
"""

from collections.abc import Callable, Iterator

import pytest
from alembic import command
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.models import User
from app.db.session import build_engine, get_db, ping_database
from app.domain.enums import UserRole
from app.main import create_app
from tests.db_utils import alembic_config
from tests.factories import make_user


@pytest.fixture(scope="session")
def test_database_url() -> str:
    return get_settings().test_database_url


@pytest.fixture(scope="session")
def db_engine(test_database_url: str) -> Iterator[Engine]:
    engine = build_engine(test_database_url, connect_timeout=3)
    try:
        ping_database(engine)
    except OperationalError as exc:
        pytest.fail(
            "Test database is not reachable. Start it with `docker compose up -d db` "
            f"or set TEST_DATABASE_URL. ({exc.__class__.__name__})"
        )
    # Start every test session from a clean, fully migrated schema.
    config = alembic_config(test_database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine: Engine) -> Iterator[Session]:
    connection = db_engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def app(request: pytest.FixtureRequest) -> FastAPI:
    application = create_app()
    if "db_session" in request.fixturenames:
        session: Session = request.getfixturevalue("db_session")
        application.dependency_overrides[get_db] = lambda: session
    return application


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin(db_session: Session) -> User:
    return make_user(db_session, "admin@test.example", UserRole.ADMIN)


@pytest.fixture
def agent(db_session: Session) -> User:
    return make_user(db_session, "agent@test.example", UserRole.AGENT_USER)


@pytest.fixture
def auth_headers() -> Callable[[User], dict[str, str]]:
    def build(user: User) -> dict[str, str]:
        token = create_access_token(user.id, user.role, get_settings())
        return {"Authorization": f"Bearer {token}"}

    return build


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Mark every test that touches the database, so `pytest -m "not db"` runs without Docker."""
    for item in items:
        if "db_engine" in getattr(item, "fixturenames", ()):
            item.add_marker(pytest.mark.db)
