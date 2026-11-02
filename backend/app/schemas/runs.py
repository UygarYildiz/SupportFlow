from datetime import datetime
from typing import Any

from app.agent.schemas import AnalysisResult
from app.domain.enums import AgentRunStatus
from app.schemas.common import ApiModel


class RunStepOut(ApiModel):
    sequence: int
    node: str
    status: str
    summary: dict[str, Any]
    duration_ms: int


class RunOut(ApiModel):
    id: int
    ticket_id: int
    requested_by: int | None
    status: AgentRunStatus
    model: str | None
    prompt_version: str | None
    result: AnalysisResult | None
    error_code: str | None
    error_message: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    steps: list[RunStepOut]
