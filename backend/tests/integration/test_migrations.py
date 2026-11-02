from alembic import command
from sqlalchemy import Engine, inspect

from tests.db_utils import alembic_config

EXPECTED_TABLES = {"users", "customers", "orders", "tickets", "ticket_events"}


def test_migrations_downgrade_to_base_and_upgrade_back(
    test_database_url: str, db_engine: Engine
) -> None:
    config = alembic_config(test_database_url)

    command.downgrade(config, "base")
    assert EXPECTED_TABLES.isdisjoint(inspect(db_engine).get_table_names())

    command.upgrade(config, "head")
    assert set(inspect(db_engine).get_table_names()) >= EXPECTED_TABLES
