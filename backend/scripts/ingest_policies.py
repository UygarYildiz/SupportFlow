"""Index the NovaShop policy documents for retrieval (ADR-014).

Usage (from backend/):
    uv run poe ingest              # embed with EMBEDDING_MODE (default: fake, offline)
    uv run poe ingest --fake       # always the offline embedder

Idempotent: unchanged documents are skipped; a document whose `version` was raised
supersedes the previous version; a document edited without raising its version is
refused. The folder holds the current version of each policy.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.agent.llm.factory import build_embedder
from app.agent.llm.fake_embeddings import FakeEmbedder
from app.core.config import get_settings
from app.db.models.knowledge import EMBEDDING_DIMENSIONS
from app.db.session import get_engine
from app.services.policy_knowledge import (
    PolicyIngestionError,
    PolicyIngestionService,
    PolicySource,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = BACKEND_DIR / "knowledge" / "policies"


def load_policy_sources(directory: Path = KNOWLEDGE_DIR) -> list[PolicySource]:
    return [
        PolicySource(path=path.relative_to(BACKEND_DIR).as_posix(), text=path.read_text("utf-8"))
        for path in sorted(directory.glob("*.md"))
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fake", action="store_true", help="use the offline embedder")
    args = parser.parse_args()

    embedder = FakeEmbedder(EMBEDDING_DIMENSIONS) if args.fake else build_embedder(get_settings())
    sources = load_policy_sources()
    with Session(get_engine()) as session:
        try:
            summary = PolicyIngestionService(session, embedder).ingest(sources)
        except PolicyIngestionError as exc:
            print(f"Ingestion failed: {exc}", file=sys.stderr)
            return 1
    print(
        f"Policies indexed with {embedder.model_name}: {summary.documents_added} added, "
        f"{summary.versions_superseded} superseded, {summary.unchanged} unchanged, "
        f"{summary.chunks_embedded} clauses embedded"
    )
    print("Current: " + ", ".join(summary.current))
    return 0


if __name__ == "__main__":
    sys.exit(main())
