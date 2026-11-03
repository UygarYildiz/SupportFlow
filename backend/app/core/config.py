"""Application settings, loaded from environment variables and the repo-root `.env` file."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]

# Development-only fallback. Production refuses to start with it (see validator).
DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0123456789"  # noqa: S105
MIN_SETUP_TOKEN_LENGTH = 16


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: Literal["development", "test", "production"] = "development"
    # ADR-017. `demo`: synthetic NovaShop data and public demo logins (local dev, live demo).
    # `self_hosted`: one business's own installation; no demo data, first-run setup instead.
    deployment_mode: Literal["demo", "self_hosted"] = "demo"
    # One-time code the first-run setup asks for, so whoever reaches a fresh installation
    # first cannot claim it. Required for self_hosted production; useless after setup.
    setup_token: SecretStr | None = None
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
    # Policy RAG embeddings (ADR-014). `fake` is a deterministic offline embedder.
    embedding_mode: Literal["fake", "live"] = "fake"
    gemini_embedding_model: str = "gemini-embedding-2"
    # Per-run limits of the analysis graph (Phase 4).
    agent_max_tokens_per_run: int = 12_000
    agent_run_timeout_seconds: float = 120.0
    # Pending action proposals expire if nobody decides in time; they never auto-execute.
    proposal_ttl_hours: int = 48
    # Read-only MCP tools (ADR-015). `mcp`: the agent reads orders and ticket history
    # through the in-process MCP server; `direct`: through the services (fallback).
    agent_tool_transport: Literal["mcp", "direct"] = "mcp"
    mcp_tool_timeout_seconds: float = 10.0
    # Staff access token the stdio MCP server acts with (`poe mcp-token`).
    mcp_access_token: SecretStr | None = None
    # Comma-separated browser origins allowed to call the API (live demo: the Cloudflare
    # Pages URL). Empty: no CORS headers; in development Vite proxies the API instead.
    cors_allow_origins: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_allow_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _require_real_secret_in_production(self) -> "Settings":
        secret = self.jwt_secret_key.get_secret_value()
        if self.app_env == "production" and (secret == DEV_JWT_SECRET or len(secret) < 32):
            raise ValueError("JWT_SECRET_KEY must be set to a random value of 32+ characters")
        if self.deployment_mode == "self_hosted" and self.app_env == "production":
            token = self.setup_token.get_secret_value() if self.setup_token else ""
            if len(token) < MIN_SETUP_TOKEN_LENGTH:
                raise ValueError(
                    f"SETUP_TOKEN must be set to a random value of {MIN_SETUP_TOKEN_LENGTH}+ "
                    "characters when DEPLOYMENT_MODE=self_hosted"
                )
        if self.llm_mode == "live" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when LLM_MODE=live")
        if self.embedding_mode == "live" and not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required when EMBEDDING_MODE=live")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
