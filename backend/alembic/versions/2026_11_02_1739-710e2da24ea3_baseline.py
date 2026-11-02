"""Baseline: empty schema. Verifies the migration pipeline; tables arrive in Phase 2.

Revision ID: 710e2da24ea3
Revises: 
Create Date: 2026-11-02 17:39:58.666038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '710e2da24ea3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
