"""Policy knowledge base for retrieval with citations (Phase 7, ADR-014)."""

from datetime import date, datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import TZDateTime, str_enum, utcnow
from app.domain.enums import IngestionStatus

# Fixed by the column type; embedders are asked for exactly this many dimensions.
EMBEDDING_DIMENSIONS = 768


class PolicyDocument(Base):
    """One version of one policy document. Old versions stay for traceability."""

    __tablename__ = "policy_documents"
    __table_args__ = (
        UniqueConstraint("slug", "version", name="uq_policy_documents_slug_version"),
        # Retrieval only ever sees one version per policy.
        Index(
            "uq_policy_documents_one_current_per_slug",
            "slug",
            unique=True,
            postgresql_where=text("is_current"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(200))
    effective_from: Mapped[date] = mapped_column(Date)
    content_hash: Mapped[str] = mapped_column(String(64))
    source_path: Mapped[str] = mapped_column(String(300))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)

    chunks: Mapped[list["PolicyChunk"]] = relationship(
        back_populates="document", order_by="PolicyChunk.position"
    )


class PolicyChunk(Base):
    """One clause of a document, embedded with one model (vectors of different models
    are never compared, so re-indexing with another model adds rows)."""

    __tablename__ = "policy_chunks"
    __table_args__ = (
        UniqueConstraint(
            "document_id", "clause_id", "embedding_model", name="uq_policy_chunks_clause_model"
        ),
        Index(
            "ix_policy_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("policy_documents.id"), index=True)
    clause_id: Mapped[str] = mapped_column(String(32))
    heading: Mapped[str] = mapped_column(String(200))
    text: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    embedding_model: Mapped[str] = mapped_column(String(100))
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))

    document: Mapped[PolicyDocument] = relationship(back_populates="chunks")


class IngestionJob(Base):
    """One indexing run over the knowledge base folder."""

    __tablename__ = "ingestion_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    status: Mapped[IngestionStatus] = mapped_column(
        str_enum(IngestionStatus, "ingestion_status"), default=IngestionStatus.RUNNING
    )
    embedding_model: Mapped[str] = mapped_column(String(100))
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(TZDateTime)
