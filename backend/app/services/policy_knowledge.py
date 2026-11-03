"""Policy knowledge base: indexing and retrieval (Phase 7, ADR-014).

Indexing is idempotent: a document is identified by (slug, version) and its
content hash. Re-running changes nothing; a new version supersedes the old one
(only one version per policy is ever searched); editing a document without
bumping its version is refused, so citations always point at the text that was
indexed under that version.

The embedder is injected (this module must not import `app.agent` or a provider
SDK); vectors are tagged with the embedder's model name and only compared with
vectors of the same model.
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.knowledge import IngestionJob, PolicyChunk, PolicyDocument
from app.db.types import utcnow
from app.domain.enums import IngestionStatus
from app.domain.policy_documents import ParsedPolicyDocument, parse_policy_document

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    @property
    def model_name(self) -> str: ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


@dataclass(frozen=True)
class PolicySource:
    path: str  # repo-relative, stored for traceability
    text: str


@dataclass
class IngestionSummary:
    job_id: int
    status: IngestionStatus
    documents_added: int = 0
    versions_superseded: int = 0
    unchanged: int = 0
    chunks_embedded: int = 0
    error: str | None = None
    current: list[str] = field(default_factory=list)  # "returns v1", ...

    def as_stats(self) -> dict[str, object]:
        return {
            "documents_added": self.documents_added,
            "versions_superseded": self.versions_superseded,
            "unchanged": self.unchanged,
            "chunks_embedded": self.chunks_embedded,
            "current": self.current,
        }


class PolicyIngestionError(Exception):
    """The knowledge base cannot be indexed as given (message says why)."""


@dataclass(frozen=True)
class PolicyExcerpt:
    """A retrieved clause, with everything needed to cite it."""

    chunk_id: int
    policy_id: str  # document slug, e.g. "returns"
    title: str
    version: int
    effective_from: date
    clause_id: str
    heading: str
    text: str
    score: float  # cosine similarity, 1.0 = identical


class PolicyIngestionService:
    def __init__(self, session: Session, embedder: Embedder) -> None:
        self.session = session
        self.embedder = embedder

    def ingest(self, sources: Iterable[PolicySource]) -> IngestionSummary:
        job = IngestionJob(embedding_model=self.embedder.model_name)
        self.session.add(job)
        self.session.commit()
        summary = IngestionSummary(job_id=job.id, status=IngestionStatus.RUNNING)
        try:
            parsed = [(s.path, parse_policy_document(s.text, name=s.path)) for s in sources]
            _reject_duplicates(parsed)
            for path, document in parsed:
                self._ingest_one(path, document, summary)
            summary.current = [f"{d.slug} v{d.version}" for d in self._current_documents()]
            summary.status = IngestionStatus.SUCCEEDED
            self.session.flush()
        except Exception as exc:  # recorded on the job, then re-raised
            self.session.rollback()
            summary.status = IngestionStatus.FAILED
            summary.error = str(exc)[:500]
            job = self.session.get(IngestionJob, summary.job_id)
            if job is None:  # pragma: no cover - committed above
                raise
            job.status, job.error, job.finished_at = summary.status, summary.error, utcnow()
            job.stats = summary.as_stats()
            self.session.commit()
            raise
        job.status, job.finished_at, job.stats = summary.status, utcnow(), summary.as_stats()
        self.session.commit()
        logger.info("Policy ingestion %s: %s", job.id, summary.as_stats())
        return summary

    def _ingest_one(
        self, path: str, document: ParsedPolicyDocument, summary: IngestionSummary
    ) -> None:
        existing = self.session.scalar(
            select(PolicyDocument).where(
                PolicyDocument.slug == document.slug, PolicyDocument.version == document.version
            )
        )
        if existing is not None:
            if existing.content_hash != document.content_hash:
                raise PolicyIngestionError(
                    f"{path}: '{document.slug}' v{document.version} içeriği değişmiş ama sürüm "
                    "artırılmamış; değişiklik için version değerini yükseltin"
                )
            added = self._embed_missing(existing, document)
            summary.chunks_embedded += added
            summary.unchanged += 1 if added == 0 else 0
            return

        current = self.session.scalar(
            select(PolicyDocument).where(
                PolicyDocument.slug == document.slug, PolicyDocument.is_current.is_(True)
            )
        )
        if current is not None and current.version > document.version:
            raise PolicyIngestionError(
                f"{path}: '{document.slug}' v{document.version}, güncel v{current.version}'den eski"
            )
        if current is not None:
            current.is_current = False
            self.session.flush()  # the partial unique index allows one current version
            summary.versions_superseded += 1

        row = PolicyDocument(
            slug=document.slug,
            version=document.version,
            title=document.title,
            effective_from=document.effective_from,
            content_hash=document.content_hash,
            source_path=path,
            is_current=True,
        )
        self.session.add(row)
        self.session.flush()
        summary.documents_added += 1
        summary.chunks_embedded += self._embed_missing(row, document)

    def _embed_missing(self, row: PolicyDocument, document: ParsedPolicyDocument) -> int:
        model = self.embedder.model_name
        have = set(
            self.session.scalars(
                select(PolicyChunk.clause_id).where(
                    PolicyChunk.document_id == row.id, PolicyChunk.embedding_model == model
                )
            )
        )
        missing = [clause for clause in document.clauses if clause.clause_id not in have]
        if not missing:
            return 0
        # The heading is part of what is embedded: it often carries the key term.
        vectors = self.embedder.embed_documents(
            [f"{document.title} {c.clause_id} {c.heading}. {c.text}" for c in missing]
        )
        for clause, vector in zip(missing, vectors, strict=True):
            self.session.add(
                PolicyChunk(
                    document_id=row.id,
                    clause_id=clause.clause_id,
                    heading=clause.heading,
                    text=clause.text,
                    position=clause.position,
                    embedding_model=model,
                    embedding=vector,
                )
            )
        self.session.flush()
        return len(missing)

    def _current_documents(self) -> list[PolicyDocument]:
        stmt = (
            select(PolicyDocument)
            .where(PolicyDocument.is_current.is_(True))
            .order_by(PolicyDocument.slug)
        )
        return list(self.session.scalars(stmt))


class PolicySearchService:
    def __init__(self, session: Session, embedder: Embedder) -> None:
        self.session = session
        self.embedder = embedder

    def search(
        self, query: str, *, policy_ids: Iterable[str] | None = None, limit: int = 3
    ) -> list[PolicyExcerpt]:
        """Clauses of the current policy versions closest to `query`, best first.

        Only vectors made by the same embedding model are compared; an empty list
        means nothing is indexed for this model (or for these policies).
        """
        vector = self.embedder.embed_query(query)
        distance = PolicyChunk.embedding.cosine_distance(vector)
        stmt = (
            select(PolicyChunk, PolicyDocument, distance.label("distance"))
            .join(PolicyDocument, PolicyChunk.document_id == PolicyDocument.id)
            .where(
                PolicyDocument.is_current.is_(True),
                PolicyChunk.embedding_model == self.embedder.model_name,
            )
            .order_by(distance, PolicyChunk.id)
            .limit(limit)
        )
        wanted = list(policy_ids) if policy_ids is not None else None
        if wanted is not None:
            stmt = stmt.where(PolicyDocument.slug.in_(wanted))
        return [
            PolicyExcerpt(
                chunk_id=chunk.id,
                policy_id=document.slug,
                title=document.title,
                version=document.version,
                effective_from=document.effective_from,
                clause_id=chunk.clause_id,
                heading=chunk.heading,
                text=chunk.text,
                score=round(1.0 - float(dist), 4),
            )
            for chunk, document, dist in self.session.execute(stmt)
        ]


def _reject_duplicates(parsed: list[tuple[str, ParsedPolicyDocument]]) -> None:
    seen: dict[str, str] = {}
    for path, document in parsed:
        if document.slug in seen:
            raise PolicyIngestionError(
                f"'{document.slug}' iki dosyada tanımlı: {seen[document.slug]} ve {path}"
            )
        seen[document.slug] = path
