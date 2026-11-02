"""Test doubles for the LLM layer and the agent's tools."""

import json
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from app.agent.llm.base import LLMClient, LLMResponse
from app.agent.tools import ALLOWED_TOOLS, ToolCall, ToolNotAllowedError

ScriptItem = LLMResponse | Exception | dict[str, Any] | str


class ScriptedLLMClient:
    """Returns (or raises) the scripted items in order and records every call."""

    model_name = "scripted-llm"

    def __init__(self, *script: ScriptItem) -> None:
        self.script = list(script)
        self.prompts: list[str] = []
        self.schemas: list[str] = []

    def generate_structured(
        self, *, system_instruction: str, prompt: str, response_schema: type[BaseModel]
    ) -> LLMResponse:
        self.prompts.append(prompt)
        self.schemas.append(response_schema.__name__)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, LLMResponse):
            return item
        text = item if isinstance(item, str) else json.dumps(item)
        return LLMResponse(text=text, model=self.model_name, input_tokens=100, output_tokens=50)


def intent_output(**overrides: Any) -> dict[str, Any]:
    """A valid IntentClassification payload (first model call)."""
    return {
        "category": "delivery_delay",
        "suggested_priority": "medium",
        "referenced_order_id": None,
        "requested_new_address": None,
        "instructions_aimed_at_system": False,
    } | overrides


def draft_output(**overrides: Any) -> dict[str, Any]:
    """A valid DraftReply payload (second model call)."""
    return {
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


@dataclass
class InMemoryTools:
    """Allowlisted tools over in-memory facts, for graph unit tests without a database."""

    orders: dict[str, Any] = field(default_factory=dict)  # order_id -> OrderFact
    policies: dict[tuple[str, str], Any] = field(default_factory=dict)  # (policy, id) -> check
    tickets: list[Any] = field(default_factory=list)
    calls: list[ToolCall] = field(default_factory=list)

    def call(self, name: str, **arguments: Any) -> Any:
        if name not in ALLOWED_TOOLS:
            raise ToolNotAllowedError(name)
        handlers = {
            "get_order": lambda order_id: self.orders.get(order_id),
            "get_customer_orders": lambda limit=10: list(self.orders.values())[:limit],
            "get_customer_tickets": lambda exclude_ticket_id, limit=5: self.tickets[:limit],
            "get_policy": lambda policy, order_id: self.policies.get((policy, order_id)),
        }
        result = handlers[name](**arguments)
        self.calls.append(ToolCall(name, arguments, result is not None and result != []))
        return result


@dataclass
class ListRecorder:
    steps: list[tuple[str, str, dict[str, Any]]] = field(default_factory=list)

    def record(self, node: str, status: str, summary: dict[str, Any], duration_ms: int) -> None:
        self.steps.append((node, status, summary))

    @property
    def nodes(self) -> list[str]:
        return [node for node, _, _ in self.steps]
