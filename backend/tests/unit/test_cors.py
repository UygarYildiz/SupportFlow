"""CORS for the live demo: only the configured frontend origin may call the API."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

FRONTEND = "https://supportflow.pages.dev"


@pytest.fixture
def client_with(monkeypatch: pytest.MonkeyPatch) -> Iterator:
    def build(origins: str) -> TestClient:
        monkeypatch.setenv("CORS_ALLOW_ORIGINS", origins)
        get_settings.cache_clear()
        return TestClient(create_app(recover_interrupted_runs=False))

    yield build
    get_settings.cache_clear()


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/api/v1/tickets",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )


def test_the_configured_frontend_may_call_the_api(client_with) -> None:
    client = client_with(f"{FRONTEND}/, http://localhost:5173")

    response = _preflight(client, FRONTEND)

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == FRONTEND
    assert "authorization" in response.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in response.headers  # bearer tokens only
    assert (
        client.get("/health", headers={"Origin": FRONTEND}).headers["access-control-allow-origin"]
        == FRONTEND
    )


def test_other_origins_get_no_cors_permission(client_with) -> None:
    client = client_with(FRONTEND)

    response = _preflight(client, "https://evil.example")

    assert "access-control-allow-origin" not in response.headers
    assert (
        "access-control-allow-origin"
        not in client.get("/health", headers={"Origin": "https://evil.example"}).headers
    )


def test_without_configuration_there_are_no_cors_headers(client_with) -> None:
    client = client_with("")

    response = client.get("/health", headers={"Origin": FRONTEND})

    assert "access-control-allow-origin" not in response.headers
