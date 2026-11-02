"""Shared test fixtures.

Tests marked `db` need the Postgres test database from compose.yaml
(`docker compose up -d db`). Its URL comes from TEST_DATABASE_URL
(environment or repo-root .env).
"""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from app.core.config import get_settings
from app.db.session import build_engine, ping_database
from app.main import create_app


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
    yield engine
    engine.dispose()


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
