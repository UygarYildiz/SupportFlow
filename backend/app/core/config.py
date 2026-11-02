"""Application settings, loaded from environment variables and the repo-root `.env` file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


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


@lru_cache
def get_settings() -> Settings:
    return Settings()
