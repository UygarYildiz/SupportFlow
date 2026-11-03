"""Indexing the policy knowledge base is idempotent and versioned; search sees only the
current version and only vectors of the same model (ADR-014)."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agent.llm.fake_embeddings import FakeEmbedder
from app.db.models.knowledge import IngestionJob, PolicyChunk, PolicyDocument
from app.domain.enums import IngestionStatus
from app.services.policy_knowledge import (
    PolicyIngestionError,
    PolicyIngestionService,
    PolicySearchService,
    PolicySource,
)
from scripts.ingest_policies import load_policy_sources

EMBEDDER = FakeEmbedder(768)

RETURNS_V1 = """---
id: returns
title: İade Politikası
version: 1
effective_from: 2026-01-01
---

## IADE-1 İade süresi

Ürün teslimattan sonraki 14 gün içinde iade edilebilir.

## IADE-2 Geri ödeme

Geri ödeme ödeme yöntemine yapılır.
"""
RETURNS_V2 = (
    RETURNS_V1.replace("version: 1", "version: 2")
    .replace("2026-01-01", "2026-06-01")
    .replace("14 gün", "30 gün")
)
ADDRESS = """---
id: address_change
title: Adres Değişikliği Politikası
version: 1
effective_from: 2026-01-01
---

## ADRES-1 Ne zaman mümkün

Adres yalnızca kargoya verilmeden önce değiştirilebilir.
"""


def ingest(session: Session, *texts: str, embedder: FakeEmbedder = EMBEDDER):
    sources = [PolicySource(path=f"knowledge/{i}.md", text=t) for i, t in enumerate(texts)]
    return PolicyIngestionService(session, embedder).ingest(sources)


def count(session: Session, model: type) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_the_real_knowledge_base_indexes_and_answers(db_session: Session) -> None:
    summary = PolicyIngestionService(db_session, EMBEDDER).ingest(load_policy_sources())
    assert summary.status == IngestionStatus.SUCCEEDED
    assert summary.documents_added == 5
    assert summary.current == [
        "address_change v1",
        "damaged_goods v1",
        "delivery v1",
        "exceptions v1",
        "returns v1",
    ]
    hits = PolicySearchService(db_session, EMBEDDER).search(
        "Kargoya verilmiş siparişin adresi değiştirilebilir mi?", limit=1
    )
    assert hits[0].policy_id == "address_change"
    assert hits[0].clause_id.startswith("ADRES-")


def test_indexing_twice_changes_nothing(db_session: Session) -> None:
    first = ingest(db_session, RETURNS_V1, ADDRESS)
    second = ingest(db_session, RETURNS_V1, ADDRESS)
    assert (first.documents_added, first.chunks_embedded) == (2, 3)
    assert (second.documents_added, second.unchanged, second.chunks_embedded) == (0, 2, 0)
    assert count(db_session, PolicyDocument) == 2
    assert count(db_session, PolicyChunk) == 3


def test_a_new_version_supersedes_the_old_one_for_search(db_session: Session) -> None:
    """TC-15: after re-indexing a changed policy, answers come from the new version."""
    ingest(db_session, RETURNS_V1)
    summary = ingest(db_session, RETURNS_V2)
    assert summary.versions_superseded == 1

    hits = PolicySearchService(db_session, EMBEDDER).search("iade süresi kaç gün", limit=5)
    assert {(h.policy_id, h.version) for h in hits} == {("returns", 2)}
    assert "30 gün" in next(h.text for h in hits if h.clause_id == "IADE-1")
    # The old version is kept for traceability, just not searched.
    versions = db_session.scalars(
        select(PolicyDocument.version).where(PolicyDocument.is_current.is_(False))
    ).all()
    assert versions == [1]


def test_editing_a_document_without_a_new_version_is_refused(db_session: Session) -> None:
    ingest(db_session, RETURNS_V1)
    with pytest.raises(PolicyIngestionError, match="sürüm artırılmamış"):
        ingest(db_session, RETURNS_V1.replace("14 gün", "20 gün"))

    job = db_session.scalars(select(IngestionJob).order_by(IngestionJob.id.desc())).first()
    assert job is not None
    assert job.status == IngestionStatus.FAILED
    assert "sürüm artırılmamış" in (job.error or "")
    text = db_session.scalar(select(PolicyChunk.text).where(PolicyChunk.clause_id == "IADE-1"))
    assert "14 gün" in (text or "")


def test_an_older_version_cannot_replace_a_newer_one(db_session: Session) -> None:
    ingest(db_session, RETURNS_V2)
    with pytest.raises(PolicyIngestionError, match="eski"):
        ingest(db_session, RETURNS_V1)


def test_search_can_be_limited_to_the_policies_a_rule_needs(db_session: Session) -> None:
    ingest(db_session, RETURNS_V1, ADDRESS)
    hits = PolicySearchService(db_session, EMBEDDER).search(
        "adres değişikliği", policy_ids=["returns"], limit=5
    )
    assert hits
    assert {h.policy_id for h in hits} == {"returns"}


class OtherModelEmbedder(FakeEmbedder):
    @property
    def model_name(self) -> str:
        return "other-embedding@768"


def test_vectors_of_another_model_are_never_compared(db_session: Session) -> None:
    ingest(db_session, RETURNS_V1, embedder=OtherModelEmbedder(768))
    assert PolicySearchService(db_session, EMBEDDER).search("iade") == []
    # Indexing the same document with the default model adds its own vectors.
    summary = ingest(db_session, RETURNS_V1)
    assert (summary.documents_added, summary.chunks_embedded) == (0, 2)
    assert PolicySearchService(db_session, EMBEDDER).search("iade")
