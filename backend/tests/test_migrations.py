from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, inspect

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    # Keep pytest's log capture intact.
    config.attributes["configure_logger"] = False
    return config


@pytest.mark.db
def test_migrations_upgrade_and_downgrade_cleanly(
    test_database_url: str, db_engine: Engine
) -> None:
    config = _alembic_config(test_database_url)

    command.downgrade(config, "base")
    command.upgrade(config, "head")
    assert "alembic_version" in inspect(db_engine).get_table_names()

    command.downgrade(config, "base")
    command.upgrade(config, "head")
