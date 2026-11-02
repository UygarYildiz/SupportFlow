"""Engine and session management (synchronous SQLAlchemy, see ADR-004)."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def build_engine(database_url: str, connect_timeout: int) -> Engine:
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": connect_timeout},
    )


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    return build_engine(settings.database_url, settings.database_connect_timeout)


@lru_cache
def _session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, always closed."""
    session = _session_factory()()
    try:
        yield session
    finally:
        session.close()


def ping_database(engine: Engine) -> None:
    """Raise if the database cannot answer a trivial query."""
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
