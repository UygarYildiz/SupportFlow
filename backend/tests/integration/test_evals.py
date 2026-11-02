"""The scenario evals (evals/scenarios.jsonl) as a regression test, with the fake model."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from app.agent.llm.fake import FakeLLMClient
from evals.runner import load_scenarios, run_scenarios

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
SCENARIOS = load_scenarios()


def test_scenario_file_covers_every_requirement_scenario_and_p0_case() -> None:
    sources = " ".join(s.source for s in SCENARIOS)
    for required in ("S1", "S2", "S3", "S4", "S5", "S6", "TC-05", "TC-06", "TC-07", "TC-10"):
        assert required in sources, f"no scenario for {required}"


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s.id for s in SCENARIOS])
def test_scenario_passes_with_the_fake_model(db_session: Session, scenario) -> None:
    [result] = run_scenarios(db_session, [scenario], FakeLLMClient(), lambda: NOW)

    failures = [f"{c.name}: {c.detail}" for c in result.checks if not c.passed]
    assert failures == []


def test_a_wrong_expectation_is_reported_as_a_critical_failure(db_session: Session) -> None:
    """Guards against checks that can never fail."""
    s3 = next(s for s in SCENARIOS if s.id == "S3-address-change-before-shipping")
    wrong = s3.model_copy(
        update={"expect": s3.expect.model_copy(update={"proposal": None, "new_address": None})}
    )

    [result] = run_scenarios(db_session, [wrong], FakeLLMClient(), lambda: NOW)

    assert [c.name for c in result.critical_failures] == ["proposed write action"]
