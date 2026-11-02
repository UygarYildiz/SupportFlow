"""Data contracts of the analysis pipeline.

`TicketAnalysis` is what the model must return. Everything in it is an untrusted
suggestion: the backend validates it and verifies cited order IDs against the
facts it actually retrieved (`AnalysisResult`).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import OrderStatus, TicketCategory, TicketPriority, TicketStatus


class OrderFact(BaseModel):
    id: str
    status: OrderStatus
    items: list[str]
    total: str
    shipping_address: str
    created_at: datetime
    shipped_at: datetime | None
    delivered_at: datetime | None


class TicketFacts(BaseModel):
    """Everything the model is allowed to know. Retrieved by the backend, scoped to one customer."""

    ticket_id: int
    subject: str
    message: str
    customer_name: str
    linked_order_id: str | None
    orders: list[OrderFact]
    # Order IDs mentioned in the message that do not exist for this customer.
    unknown_order_ids: list[str]
    reference_time: datetime

    def known_order_ids(self) -> set[str]:
        return {order.id for order in self.orders}


class TicketAnalysis(BaseModel):
    """Structured output requested from the LLM."""

    model_config = ConfigDict(extra="forbid")

    category: TicketCategory
    suggested_priority: TicketPriority
    summary: str = Field(min_length=1, max_length=600, description="One or two sentences.")
    needs_human_review: bool = Field(
        description="True if the request is unusual, against policy, or facts are unclear."
    )
    draft_reply: str = Field(
        min_length=1,
        max_length=2500,
        description="Reply to the customer. Must not promise refunds or changes.",
    )
    missing_information: list[str] = Field(
        max_length=5, description="What must be asked from the customer. Empty if nothing."
    )
    evidence_order_ids: list[str] = Field(
        max_length=10, description="IDs from the provided orders that the reply relies on."
    )


class AnalysisResult(BaseModel):
    """Stored on the run. Verified data is kept apart from what the model claimed."""

    analysis: TicketAnalysis
    verified_order_ids: list[str]
    unverified_order_ids: list[str]
    warnings: list[str]
    outcome_status: TicketStatus
    prompt_version: str


class AnalysisMetrics(BaseModel):
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int


def order_fact_total(amount: Decimal, currency: str) -> str:
    return f"{amount:.2f} {currency}"
