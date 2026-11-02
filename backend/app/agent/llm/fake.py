"""Deterministic stand-in for the LLM (LLM_MODE=fake).

Used by tests, CI and the public demo: free, offline and reproducible. It reads
the same prompts the real model gets and answers with simple rules, so the
whole graph (routing, policy, validation, run bookkeeping) is exercised.
"""

import json
import re
from typing import Any

from pydantic import BaseModel

from app.agent.llm.base import LLMResponse
from app.agent.schemas import DraftReply, IntentClassification
from app.domain.enums import TicketCategory, TicketPriority

_KEYWORDS: list[tuple[TicketCategory, tuple[str, ...]]] = [
    (TicketCategory.DAMAGED_ITEM, ("damaged", "cracked", "broken", "defective")),
    (TicketCategory.ADDRESS_CHANGE, ("address", "ship it to", "send it to")),
    (TicketCategory.REFUND_REQUEST, ("refund", "return", "money back")),
    (TicketCategory.DELIVERY_DELAY, ("where is", "not arrived", "hasn't arrived", "still not",
                                     "not received", "haven't received", "delayed", "status")),
]  # fmt: skip
_FOLLOW_UP_MARKERS = (
    "previous request",
    "earlier request",
    "my last request",
    "follow-up",
    "follow up",
    "never heard back",
    "what happened to my",
)
_INJECTION_MARKERS = ("ignore all previous", "ignore previous", "you are now", "system instruction")
_ORDER_ID = re.compile(r"\bORD-\d{3,6}\b", re.IGNORECASE)
# "... to 42 Harbor St, Riverton." / "new address: 7 Cedar Rd." / "... instead?"
_NEW_ADDRESS = re.compile(
    r"(?:\bto|address:)[:\s]+(\d+[^.?!]*?)(?:\s+instead)?[.?!]", re.IGNORECASE
)


class FakeLLMClient:
    model_name = "fake-llm"

    def generate_structured(
        self, *, system_instruction: str, prompt: str, response_schema: type[BaseModel]
    ) -> LLMResponse:
        if response_schema is IntentClassification:
            output = _classify(prompt)
        elif response_schema is DraftReply:
            output = _draft(prompt)
        else:  # pragma: no cover - programming error
            raise TypeError(f"FakeLLMClient cannot answer {response_schema.__name__}")
        text = json.dumps(output)
        # Rough token estimate (~4 characters per token) so metrics are populated.
        return LLMResponse(
            text=text,
            model=self.model_name,
            input_tokens=(len(system_instruction) + len(prompt)) // 4,
            output_tokens=len(text) // 4,
        )


def _classify(prompt: str) -> dict[str, Any]:
    message = _between(prompt, "<ticket_message>", "</ticket_message>")
    lowered = message.lower()
    suspicious = any(marker in lowered for marker in _INJECTION_MARKERS)
    address = _NEW_ADDRESS.search(message)
    if suspicious:
        category = TicketCategory.UNKNOWN
    elif address and not any(word in lowered for word in ("damaged", "refund", "return")):
        category = TicketCategory.ADDRESS_CHANGE  # "please send it to 12 Main St"
    else:
        category = _category(lowered)
    if category != TicketCategory.ADDRESS_CHANGE:
        address = None
    order_ids = _ORDER_ID.findall(message)
    priority = (
        TicketPriority.HIGH
        if suspicious or category == TicketCategory.DAMAGED_ITEM
        else TicketPriority.MEDIUM
    )
    return {
        "category": category.value,
        "suggested_priority": priority.value,
        "referenced_order_id": order_ids[0].upper() if order_ids else None,
        "requested_new_address": address.group(1).strip() if address else None,
        "instructions_aimed_at_system": suspicious,
    }


def _draft(prompt: str) -> dict[str, Any]:
    facts = json.loads(_between(prompt, "<facts>", "</facts>"))
    name = facts["customer_name"]
    focus = facts["focus_order_id"]
    order = next((o for o in facts["orders"] if o["id"] == focus), None)
    denied = [c for c in facts["policy_checks"] if not c["allowed"] and not c["informational"]]
    category = facts["category"]
    message = _between(prompt, "<ticket_message>", "</ticket_message>").lower()
    follow_up = bool(facts["previous_tickets"]) and any(m in message for m in _FOLLOW_UP_MARKERS)

    if facts["missing_information"]:
        if facts["unknown_order_ids"]:
            lead = (
                f"We could not find order {', '.join(facts['unknown_order_ids'])} in your account."
            )
        else:
            lead = "Thanks for reaching out."
        body = f"{lead} Could you please send us: {'; '.join(facts['missing_information'])}?"
    elif category == TicketCategory.UNKNOWN.value:
        body = "Thanks for your message. A team member will review it shortly."
    elif denied:
        body = f"We looked into your request for order {focus}. {denied[0]['reason']}"
    elif facts["planned_action"]:
        body = (
            f"We received your request regarding order {focus}. "
            "A team member will review it and get back to you shortly."
        )
    elif follow_up:  # S6: the customer asks about an earlier ticket, not about the order
        body = _previous_tickets_text(facts["previous_tickets"])
    elif order is not None:
        checks = " ".join(c["reason"] for c in facts["policy_checks"])
        body = f"Your order {focus} is currently '{order['status']}'. {checks}".strip()
    elif facts["previous_tickets"]:
        body = _previous_tickets_text(facts["previous_tickets"])
    else:
        body = "Thanks for reaching out. A team member will get back to you shortly."

    return {
        "summary": f"Request classified as {category.replace('_', ' ')}"
        + (f" about order {focus}." if focus else "."),
        "needs_human_review": category == TicketCategory.UNKNOWN.value or bool(denied),
        "draft_reply": f"Hello {name},\n\n{body}\n\nBest regards,\nNovaShop Support",
        "missing_information": [],
        "evidence_order_ids": [focus] if order else [],
    }


def _previous_tickets_text(tickets: list[dict[str, Any]]) -> str:
    subjects = ", ".join(f"'{t['subject']}' ({t['status']})" for t in tickets)
    return f"We found your earlier requests: {subjects}. A team member will follow up."


def _category(message: str) -> TicketCategory:
    for category, keywords in _KEYWORDS:
        if any(keyword in message for keyword in keywords):
            return category
    return TicketCategory.GENERAL


def _between(text: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.DOTALL)
    return match.group(1).strip() if match else ""
