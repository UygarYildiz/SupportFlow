"""Self-hosted installation record (ADR-017): at most one row, created by first-run setup.

Revision ID: ecd76e97ec20
Revises: b7d41c2e9a10
Create Date: 2026-11-03 23:36:04.745751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ecd76e97ec20'
down_revision: Union[str, Sequence[str], None] = 'b7d41c2e9a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('installation',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('organization_name', sa.String(length=120), nullable=False),
    sa.Column('completed_by_id', sa.Integer(), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('id = 1', name=op.f('ck_installation_single_row')),
    sa.ForeignKeyConstraint(['completed_by_id'], ['users.id'], name=op.f('fk_installation_completed_by_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_installation'))
    )


def downgrade() -> None:
    op.drop_table('installation')
