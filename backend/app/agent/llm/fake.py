"""Deterministic stand-in for the LLM (LLM_MODE=fake).

Used by tests, CI and the public demo: free, offline and reproducible. It reads
the same prompt the real model gets and answers with keyword rules, so the
whole pipeline (validation, evidence checks, run bookkeeping) is exercised.
"""

import json
import re

from pydantic import BaseModel

from app.agent.llm.base import LLMResponse
from app.domain.enums import TicketCategory, TicketPriority

_KEYWORDS: list[tuple[TicketCategory, tuple[str, ...]]] = [
    (TicketCategory.DAMAGED_ITEM, ("damaged", "cracked", "broken", "defective")),
    (TicketCategory.ADDRESS_CHANGE, ("address", "ship it to", "send it to")),
    (TicketCategory.REFUND_REQUEST, ("refund", "return", "money back")),
    (TicketCategory.DELIVERY_DELAY, ("where is", "not arrived", "hasn't arrived", "still not",
                                     "not received", "haven't received", "delayed")),
]  # fmt: skip

_INJECTION_MARKERS = ("ignore all previous", "ignore previous", "you are now", "system instruction")

_REPLIES = {
    TicketCategory.DELIVERY_DELAY: "We checked order {order}: its current status is '{status}'. "
    "A team member will follow up with you if anything needs to be done.",
    TicketCategory.DAMAGED_ITEM: "We're sorry that your item from order {order} arrived damaged. "
    "A team member will review your request and get back to you shortly.",
    TicketCategory.ADDRESS_CHANGE: "We received your request to change the delivery address for "
    "order {order}. A team member will review it and confirm whether the change is possible.",
    TicketCategory.REFUND_REQUEST: "We received your request regarding order {order}. "
    "A team member will review it against our return policy and get back to you.",
    TicketCategory.GENERAL: "Thanks for reaching out. A team member will get back to you shortly.",
    TicketCategory.UNKNOWN: "Thanks for your message. A team member will review it shortly.",
}


class FakeLLMClient:
    model_name = "fake-llm"

    def generate_structured(
        self, *, system_instruction: str, prompt: str, response_schema: type[BaseModel]
    ) -> LLMResponse:
        facts = json.loads(_between(prompt, "<facts>", "</facts>"))
        message = _between(prompt, "<ticket_message>", "</ticket_message>").lower()

        suspicious = any(marker in message for marker in _INJECTION_MARKERS)
        category = TicketCategory.UNKNOWN if suspicious else _classify(message)
        orders = {order["id"]: order for order in facts["orders"]}
        linked = facts.get("linked_order_id")
        order = orders.get(linked) if linked else None
        missing: list[str] = []

        if facts["unknown_order_ids"] and order is None:
            missing.append("A valid order number for this account")
            ids = ", ".join(facts["unknown_order_ids"])
            reply = (
                f"We could not find order {ids} in your account. "
                "Could you please double-check the order number and send it to us?"
            )
        elif order is None and category not in (TicketCategory.GENERAL, TicketCategory.UNKNOWN):
            missing.append("The order number this request is about")
            reply = "Could you please tell us the order number this request is about?"
        else:
            template = _REPLIES[category]
            reply = template.format(
                order=order["id"] if order else "-", status=order["status"] if order else "-"
            )

        analysis = {
            "category": category.value,
            "suggested_priority": (
                TicketPriority.HIGH if category == TicketCategory.DAMAGED_ITEM or suspicious
                else TicketPriority.MEDIUM
            ).value,
            "summary": _summary(category, order, suspicious),
            "needs_human_review": suspicious or category == TicketCategory.REFUND_REQUEST,
            "draft_reply": (
                f"Hello {facts['customer_name']},\n\n{reply}\n\nBest regards,\nNovaShop Support"
            ),
            "missing_information": missing,
            "evidence_order_ids": [order["id"]] if order else [],
        }  # fmt: skip
        text = json.dumps(analysis)
        # Rough token estimate (~4 characters per token) so metrics are populated.
        return LLMResponse(
            text=text,
            model=self.model_name,
            input_tokens=len(prompt) // 4,
            output_tokens=len(text) // 4,
        )


def _classify(message: str) -> TicketCategory:
    for category, keywords in _KEYWORDS:
        if any(keyword in message for keyword in keywords):
            return category
    return TicketCategory.GENERAL


def _summary(category: TicketCategory, order: dict | None, suspicious: bool) -> str:
    if suspicious:
        return "The message contains instructions aimed at the system; no request was identified."
    subject = f" about order {order['id']}" if order else ""
    return f"Customer request classified as {category.value.replace('_', ' ')}{subject}."


def _between(text: str, start: str, end: str) -> str:
    match = re.search(re.escape(start) + r"(.*?)" + re.escape(end), text, re.DOTALL)
    return match.group(1).strip() if match else ""
