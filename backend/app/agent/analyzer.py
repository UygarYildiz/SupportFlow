"""Turns facts into a validated, evidence-checked analysis. No database access."""

import time

from pydantic import ValidationError

from app.agent.llm.base import LLMClient, LLMError
from app.agent.prompts import PROMPT_VERSION, SYSTEM_INSTRUCTION, build_prompt
from app.agent.schemas import AnalysisMetrics, AnalysisResult, TicketAnalysis, TicketFacts
from app.domain.enums import TicketStatus


class AnalysisError(Exception):
    """Analysis could not produce a usable result. `code` is safe to show to staff."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class TicketAnalyzer:
    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def analyze(self, facts: TicketFacts) -> tuple[AnalysisResult, AnalysisMetrics]:
        started = time.perf_counter()
        try:
            response = self.llm.generate_structured(
                system_instruction=SYSTEM_INSTRUCTION,
                prompt=build_prompt(facts),
                response_schema=TicketAnalysis,
            )
        except LLMError as exc:
            raise AnalysisError(exc.code, str(exc)) from exc
        metrics = AnalysisMetrics(
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

        try:
            analysis = TicketAnalysis.model_validate_json(response.text)
        except ValidationError as exc:
            # The raw output is not stored or logged: it may contain anything.
            raise AnalysisError(
                "invalid_output", f"Model output failed validation ({exc.error_count()} errors)"
            ) from exc

        return verify(analysis, facts), metrics


def verify(analysis: TicketAnalysis, facts: TicketFacts) -> AnalysisResult:
    """Deterministic checks the model cannot override."""
    known = facts.known_order_ids()
    verified = [order_id for order_id in analysis.evidence_order_ids if order_id in known]
    unverified = [order_id for order_id in analysis.evidence_order_ids if order_id not in known]
    warnings: list[str] = []
    needs_review = analysis.needs_human_review
    missing = list(analysis.missing_information)

    if unverified:
        warnings.append(
            f"Model cited order(s) not found for this customer: {', '.join(unverified)}. "
            "They are not shown as evidence."
        )
        needs_review = True

    if facts.unknown_order_ids and not verified:
        unknown = ", ".join(facts.unknown_order_ids)
        warnings.append(f"Order(s) mentioned by the customer were not found: {unknown}.")
        if not missing:
            missing.append("A valid order number for this account")

    checked = analysis.model_copy(
        update={
            "needs_human_review": needs_review,
            "missing_information": missing,
            "evidence_order_ids": verified,
        }
    )
    outcome = TicketStatus.NEEDS_INFO if missing else TicketStatus.AWAITING_REVIEW
    return AnalysisResult(
        analysis=checked,
        verified_order_ids=verified,
        unverified_order_ids=unverified,
        warnings=warnings,
        outcome_status=outcome,
        prompt_version=PROMPT_VERSION,
    )
