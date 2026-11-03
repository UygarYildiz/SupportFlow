"""Policy knowledge base: documents, clause embeddings (pgvector), ingestion jobs (ADR-014).

Revision ID: 29965e867c2d
Revises: 57772f46d3ca
Create Date: 2026-11-03 13:00:03.400644

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '29965e867c2d'
down_revision: Union[str, Sequence[str], None] = '57772f46d3ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('ingestion_jobs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('status', sa.Enum('running', 'succeeded', 'failed', name='ingestion_status', native_enum=False, create_constraint=True, length=32), nullable=False),
    sa.Column('embedding_model', sa.String(length=100), nullable=False),
    sa.Column('stats', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_ingestion_jobs'))
    )
    op.create_table('policy_documents',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=64), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('source_path', sa.String(length=300), nullable=False),
    sa.Column('is_current', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_policy_documents')),
    sa.UniqueConstraint('slug', 'version', name='uq_policy_documents_slug_version')
    )
    op.create_index('uq_policy_documents_one_current_per_slug', 'policy_documents', ['slug'], unique=True, postgresql_where=sa.text('is_current'))
    op.create_table('policy_chunks',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('document_id', sa.Integer(), nullable=False),
    sa.Column('clause_id', sa.String(length=32), nullable=False),
    sa.Column('heading', sa.String(length=200), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('embedding_model', sa.String(length=100), nullable=False),
    sa.Column('embedding', Vector(768), nullable=False),
    sa.ForeignKeyConstraint(['document_id'], ['policy_documents.id'], name=op.f('fk_policy_chunks_document_id_policy_documents')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_policy_chunks')),
    sa.UniqueConstraint('document_id', 'clause_id', 'embedding_model', name='uq_policy_chunks_clause_model')
    )
    op.create_index(op.f('ix_policy_chunks_document_id'), 'policy_chunks', ['document_id'], unique=False)
    op.create_index('ix_policy_chunks_embedding_hnsw', 'policy_chunks', ['embedding'], unique=False, postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_policy_chunks_embedding_hnsw', table_name='policy_chunks', postgresql_using='hnsw', postgresql_ops={'embedding': 'vector_cosine_ops'})
    op.drop_index(op.f('ix_policy_chunks_document_id'), table_name='policy_chunks')
    op.drop_table('policy_chunks')
    op.drop_index('uq_policy_documents_one_current_per_slug', table_name='policy_documents', postgresql_where=sa.text('is_current'))
    op.drop_table('policy_documents')
    op.drop_table('ingestion_jobs')
    op.execute("DROP EXTENSION IF EXISTS vector")
