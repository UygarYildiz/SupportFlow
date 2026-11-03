"""Retrieval quality of the policy knowledge base (Phase 7, ADR-014).

`evals/policy_retrieval.jsonl` lists questions and the clause(s) that answer them.
Each question is searched (optionally limited to some policies, as the analysis
graph does) and scored:

- hit@k: share of questions with an expected clause among the top k results;
- MRR: mean of 1 / rank of the first expected clause (0 when not in the results).

Usage (from backend/):
    uv run poe eval-rag            # offline embedder (what tests, CI and the demo use)
    uv run poe eval-rag --live     # gemini-embedding-2 (needs GEMINI_API_KEY; small quota)
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.services.policy_knowledge import (
    Embedder,
    PolicyIngestionService,
    PolicySearchService,
)
from scripts.ingest_policies import load_policy_sources

GOLDEN_FILE = Path(__file__).resolve().parents[2] / "evals" / "policy_retrieval.jsonl"
TOP_K = 3


class RetrievalCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    query: str
    expected: list[str]
    policies: list[str] | None = None


@dataclass(frozen=True)
class CaseResult:
    case: RetrievalCase
    ranked: list[str]  # clause ids, best first

    @property
    def rank(self) -> int | None:
        return next((i for i, c in enumerate(self.ranked, 1) if c in self.case.expected), None)


@dataclass(frozen=True)
class RetrievalReport:
    model: str
    results: list[CaseResult]

    def hit_at(self, k: int) -> float:
        hits = sum(1 for r in self.results if r.rank is not None and r.rank <= k)
        return hits / len(self.results)

    @property
    def mrr(self) -> float:
        return sum(1 / r.rank for r in self.results if r.rank) / len(self.results)


def load_cases(path: Path = GOLDEN_FILE) -> list[RetrievalCase]:
    lines = path.read_text(encoding="utf-8").splitlines()
    cases = [RetrievalCase.model_validate_json(line) for line in lines if line.strip()]
    if len({c.id for c in cases}) != len(cases):
        raise ValueError("Retrieval case ids must be unique")
    return cases


def evaluate(session: Session, embedder: Embedder, cases: list[RetrievalCase]) -> RetrievalReport:
    """Index the knowledge base with `embedder` (inside the caller's transaction) and score."""
    PolicyIngestionService(session, embedder).ingest(load_policy_sources())
    search = PolicySearchService(session, embedder)
    results = [
        CaseResult(
            case,
            [e.clause_id for e in search.search(case.query, policy_ids=case.policies, limit=TOP_K)],
        )
        for case in cases
    ]
    return RetrievalReport(embedder.model_name, results)


def print_report(report: RetrievalReport) -> None:
    print(f"\nPolicy retrieval with '{report.model}' ({len(report.results)} questions)\n")
    for result in report.results:
        mark = "PASS" if result.rank == 1 else ("TOP3" if result.rank else "MISS")
        print(f"{mark}  {result.case.id:<24} expected {result.case.expected}, got {result.ranked}")
    print(
        f"\nhit@1 {report.hit_at(1):.2f} · hit@{TOP_K} {report.hit_at(TOP_K):.2f} · "
        f"MRR {report.mrr:.2f}"
    )


def main() -> int:
    from sqlalchemy import create_engine

    from app.agent.llm.factory import build_embedder
    from app.agent.llm.fake_embeddings import FakeEmbedder
    from app.core.config import get_settings
    from app.db.models.knowledge import EMBEDDING_DIMENSIONS
    from evals.__main__ import _migrate

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="use Gemini embeddings (quota)")
    args = parser.parse_args()

    settings = get_settings()
    embedder: Embedder = (
        build_embedder(settings.model_copy(update={"embedding_mode": "live"}))
        if args.live
        else FakeEmbedder(EMBEDDING_DIMENSIONS)
    )
    _migrate(settings.test_database_url)
    engine = create_engine(settings.test_database_url)
    with engine.connect() as connection:
        outer = connection.begin()
        session = Session(bind=connection, join_transaction_mode="create_savepoint")
        try:
            report = evaluate(session, embedder, load_cases())
        finally:
            session.close()
            outer.rollback()  # never leaves data behind
    engine.dispose()
    print_report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
