from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.db.session import build_engine, get_engine


def test_health_returns_ok_without_touching_dependencies(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_reports_database_ok(app: FastAPI, client: TestClient, db_engine: Engine) -> None:
    app.dependency_overrides[get_engine] = lambda: db_engine

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_ready_returns_503_when_database_is_unreachable(app: FastAPI, client: TestClient) -> None:
    # Port 1 on localhost refuses connections immediately.
    unreachable = build_engine(
        "postgresql+psycopg://nobody:nothing@127.0.0.1:1/none", connect_timeout=1
    )
    app.dependency_overrides[get_engine] = lambda: unreachable

    response = client.get("/ready")

    assert response.status_code == 503
    body = response.json()
    assert body == {"status": "not_ready", "database": "unavailable"}
    # Driver/connection details must not leak to clients.
    assert "127.0.0.1" not in response.text
