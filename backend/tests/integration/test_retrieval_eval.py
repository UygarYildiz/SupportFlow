"""Retrieval quality on the golden set does not regress (Phase 7, `poe eval-rag`)."""

from sqlalchemy.orm import Session

from app.agent.llm.fake_embeddings import FakeEmbedder
from evals.retrieval import CaseResult, RetrievalCase, RetrievalReport, evaluate, load_cases


def test_offline_retrieval_meets_the_measured_baseline(db_session: Session) -> None:
    """Baseline measured on 2026-11-03: hit@1 0.80, hit@3 0.95, MRR 0.86 (live model:
    0.90 / 1.00 / 0.94). A change to chunking, the embedder or the documents that makes
    retrieval worse fails here."""
    report = evaluate(db_session, FakeEmbedder(768), load_cases())

    assert len(report.results) == 20
    assert report.hit_at(1) >= 0.80
    assert report.hit_at(3) >= 0.95
    assert report.mrr >= 0.85


def test_every_clause_of_the_knowledge_base_is_asked_about() -> None:
    expected = {clause for case in load_cases() for clause in case.expected}
    # 21 clauses; HASAR-1/4 share a question, IADE-1 (scope) is covered by other documents.
    assert len(expected) >= 19


def test_scores_count_the_first_expected_clause() -> None:
    def result(ranked: list[str]) -> CaseResult:
        return CaseResult(RetrievalCase(id="x", query="q", expected=["A"]), ranked)

    report = RetrievalReport("m", [result(["A", "B"]), result(["B", "A"]), result(["B", "C"])])

    assert report.hit_at(1) == 1 / 3
    assert report.hit_at(3) == 2 / 3
    assert report.mrr == (1 + 1 / 2) / 3
