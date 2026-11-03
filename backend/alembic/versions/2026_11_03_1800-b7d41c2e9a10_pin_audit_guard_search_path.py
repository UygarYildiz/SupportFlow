"""Pin the audit guard function's search_path (hardening for hosted Postgres).

Revision ID: b7d41c2e9a10
Revises: 29965e867c2d
Create Date: 2026-11-03 18:00:00

The append-only trigger function references nothing, so an empty search_path is
safe; a fixed search_path stops a caller's schema from shadowing names it resolves
(Supabase security advisor lint 0011).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b7d41c2e9a10"
down_revision: Union[str, Sequence[str], None] = "29965e867c2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER FUNCTION audit_logs_block_changes() SET search_path = ''")


def downgrade() -> None:
    op.execute("ALTER FUNCTION audit_logs_block_changes() RESET search_path")
