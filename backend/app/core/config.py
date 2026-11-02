"""Application settings, loaded from environment variables and the repo-root `.env` file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]

# Development-only fallback. Production refuses to start with it (see validator).
DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0123456789"  # noqa: S105


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://supportflow:supportflow@localhost:5433/supportflow"
    # Seconds to wait when opening a DB connection; keeps /ready fast when the DB is down.
    database_connect_timeout: int = 3
    # Separate database used only by the automated test suite.
    test_database_url: str = (
        "postgresql+psycopg://supportflow:supportflow@localhost:5433/supportflow_test"
    )

    # Demo authentication (ADR-007)
    jwt_secret_key: SecretStr = SecretStr(DEV_JWT_SECRET)
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_minutes: int = 30

    # LLM (ADR-009). `fake` is deterministic and free: used by tests, CI and the public demo.
    llm_mode: Literal["fake", "live"] = "fake"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    llm_timeout_seconds: float = 30.0
    llm_max_attempts: int = 3

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        secret = self.jwt_secret_key.get_secret_value()
        if self.app_env == "production" and (secret == DEV_JWT_SECRET or len(secret) < 32):
            raise ValueError("JWT_SECRET_KEY must be set to a random value of 32+ characters")
        if self.llm_mode == "live" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_MODE=live")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
