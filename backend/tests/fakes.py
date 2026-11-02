"""Test doubles for the LLM layer."""

import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.agent.llm.base import LLMClient, LLMResponse


class ScriptedLLMClient:
    """Returns (or raises) the scripted items in order and records every prompt."""

    model_name = "scripted-llm"

    def __init__(self, *script: LLMResponse | Exception | dict[str, Any] | str) -> None:
        self.script = list(script)
        self.prompts: list[str] = []
        self.system_instructions: list[str] = []

    def generate_structured(
        self, *, system_instruction: str, prompt: str, response_schema: type[BaseModel]
    ) -> LLMResponse:
        self.prompts.append(prompt)
        self.system_instructions.append(system_instruction)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, LLMResponse):
            return item
        text = item if isinstance(item, str) else json.dumps(item)
        return LLMResponse(text=text, model=self.model_name, input_tokens=100, output_tokens=50)


def analysis_output(**overrides: Any) -> dict[str, Any]:
    """A valid TicketAnalysis payload; override fields per test."""
    return {
        "category": "delivery_delay",
        "suggested_priority": "medium",
        "summary": "Customer asks where the order is.",
        "needs_human_review": False,
        "draft_reply": "Hello, your order is on its way.",
        "missing_information": [],
        "evidence_order_ids": [],
    } | overrides


@dataclass
class LLMSlot:
    """Lets a test swap the LLM used by the API's analysis executor."""

    client: LLMClient = field(default_factory=lambda: _default_llm())


def _default_llm() -> LLMClient:
    from app.agent.llm.fake import FakeLLMClient

    return FakeLLMClient()
