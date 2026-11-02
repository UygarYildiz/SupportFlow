"""Run the scenario evals and print a report.

Usage (from backend/, with the compose Postgres running):
    uv run poe eval                 # fake model: deterministic, free, what CI checks
    uv run poe eval --live          # real Gemini model (needs GEMINI_API_KEY); costs quota
    uv run poe eval --only S1       # scenarios whose id starts with S1

Runs against TEST_DATABASE_URL inside one transaction that is always rolled back,
so no data is left behind. Exit code 1 when a critical check fails (and, with the
fake model, when any check fails).
"""

import argparse
import sys
import time
from datetime import UTC, datetime

from alembic import command
from alembic.config import Config
from sqlalchemy.orm import Session

from app.agent.llm.base import LLMClient
from app.agent.llm.factory import build_llm_client
from app.core.config import get_settings
from app.db.session import build_engine
from evals.runner import SCENARIO_FILE, ScenarioResult, load_scenarios, run_scenarios

BACKEND_DIR = SCENARIO_FILE.parents[1] / "backend"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SupportFlow scenario evals")
    parser.add_argument("--live", action="store_true", help="use the real model (costs quota)")
    parser.add_argument("--only", default="", help="run scenarios whose id starts with this")
    parser.add_argument(
        "--pause", type=float, default=6.0, help="seconds between live scenarios (rate limits)"
    )
    args = parser.parse_args()

    settings = get_settings()
    llm: LLMClient = build_llm_client(
        settings.model_copy(update={"llm_mode": "live" if args.live else "fake"})
    )
    scenarios = [s for s in load_scenarios() if s.id.startswith(args.only)]
    if not scenarios:
        print(f"No scenario id starts with {args.only!r}")
        return 1

    url = settings.test_database_url
    _migrate(url)
    engine = build_engine(url, settings.database_connect_timeout)
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    started = time.perf_counter()
    try:
        results = run_scenarios(
            session,
            scenarios,
            llm,
            lambda: datetime.now(UTC),
            between=(lambda: time.sleep(args.pause)) if args.live else (lambda: None),
        )
    finally:
        session.close()
        outer.rollback()  # evals never leave data behind
        connection.close()
        engine.dispose()

    _report(results, llm.model_name, time.perf_counter() - started)
    critical = sum(len(r.critical_failures) for r in results)
    quality = sum(len(r.quality_failures) for r in results)
    return 1 if critical or (quality and not args.live) else 0


def _migrate(url: str) -> None:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")


def _report(results: list[ScenarioResult], model: str, seconds: float) -> None:
    print(f"\nScenario evals with model '{model}' ({seconds:.1f}s)\n")
    for result in results:
        s = result.scenario
        if result.critical_failures:
            mark = "FAIL"
        elif result.quality_failures:
            mark = "WARN"
        else:
            mark = "PASS"
        print(f"{mark}  {s.priority}  {s.id:<40} ({s.source})")
        for check in result.critical_failures + result.quality_failures:
            kind = "critical" if check.critical else "quality"
            print(f"        {kind}: {check.name}: {check.detail}")
    total = len(results)
    clean = sum(not r.critical_failures and not r.quality_failures for r in results)
    safe = sum(not r.critical_failures for r in results)
    print(f"\n{clean}/{total} fully passed, {safe}/{total} passed every critical check.")


if __name__ == "__main__":
    sys.exit(main())
