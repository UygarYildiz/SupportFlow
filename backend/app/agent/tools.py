"""The agent's tools: an explicit allowlist of read-only operations.

Every tool is bound to one customer when the run starts (taken from the ticket
in the database). Arguments produced by the model can narrow a lookup, never
widen it: another customer's order is indistinguishable from a missing one.
`search_policies` reads the shared policy knowledge base (ADR-014); its query is
built by the graph from rule results, never from customer text.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.schemas import (
    OrderFact,
    PolicyCheck,
    PolicyExcerptFact,
    PreviousTicketFact,
    order_fact_total,
)
from app.db.models import Order, Ticket
from app.domain.errors import NotFoundError
from app.services.orders import OrderService
from app.services.policy import PolicyService
from app.services.policy_knowledge import Embedder, PolicySearchService

PolicyName = Literal["address_change", "return", "damage", "delivery"]

# Policies that describe a situation rather than grant or refuse a request.
INFORMATIONAL_POLICIES = frozenset({"delivery"})

ALLOWED_TOOLS = frozenset(
    {"get_order", "get_customer_orders", "get_customer_tickets", "get_policy", "search_policies"}
)
# Tool arguments that are not copied into the recorded run steps (kept small and text-free).
UNRECORDED_ARGUMENTS = frozenset({"query"})


class ToolNotAllowedError(Exception):
    pass


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any]
    found: bool


class AgentTools(Protocol):
    calls: list[ToolCall]

    def call(self, name: str, **arguments: Any) -> Any: ...


@dataclass
class DatabaseTools:
    """Allowlisted, customer-scoped, read-only tools backed by the domain services."""

    session: Session
    customer_id: str
    clock: Callable[[], datetime]
    embedder: Embedder | None = None  # None: no knowledge base, searches find nothing
    calls: list[ToolCall] = field(default_factory=list)

    def call(self, name: str, **arguments: Any) -> Any:
        if name not in ALLOWED_TOOLS:
            raise ToolNotAllowedError(f"Tool '{name}' is not allowed")
        result = getattr(self, f"_{name}")(**arguments)
        found = result is not None and result != []
        self.calls.append(ToolCall(name=name, arguments=arguments, found=found))
        return result

    def _get_order(self, order_id: str) -> OrderFact | None:
        try:
            order = OrderService(self.session).get_customer_order(self.customer_id, order_id)
        except NotFoundError:
            return None
        return order_fact(order)

    def _get_customer_orders(self, limit: int = 10) -> list[OrderFact]:
        orders = OrderService(self.session).list_customer_orders(self.customer_id)
        return [order_fact(order) for order in orders[:limit]]

    def _get_customer_tickets(
        self, exclude_ticket_id: int, limit: int = 5
    ) -> list[PreviousTicketFact]:
        stmt = (
            select(Ticket)
            .where(Ticket.customer_id == self.customer_id, Ticket.id != exclude_ticket_id)
            .order_by(Ticket.created_at.desc())
            .limit(limit)
        )
        return [
            PreviousTicketFact(
                id=ticket.id,
                subject=ticket.subject,
                status=ticket.status,
                created_at=ticket.created_at,
            )
            for ticket in self.session.scalars(stmt)
        ]

    def _get_policy(self, policy: PolicyName, order_id: str) -> PolicyCheck | None:
        service = PolicyService(OrderService(self.session), clock=self.clock)
        checks = {
            "address_change": service.address_change,
            "return": service.return_request,
            "damage": service.damage_report,
            "delivery": service.delivery,
        }
        try:
            decision = checks[policy](self.customer_id, order_id)
        except NotFoundError:
            return None
        return PolicyCheck(
            rule=decision.rule,
            order_id=order_id,
            allowed=decision.allowed,
            reason=decision.reason,
            informational=policy in INFORMATIONAL_POLICIES,
        )

    def _search_policies(
        self, policy_ids: list[str], query: str, limit: int = 2
    ) -> list[PolicyExcerptFact]:
        if self.embedder is None or not policy_ids:
            return []
        excerpts = PolicySearchService(self.session, self.embedder).search(
            query, policy_ids=policy_ids, limit=limit
        )
        return [
            PolicyExcerptFact(
                policy_id=e.policy_id,
                title=e.title,
                version=e.version,
                effective_from=e.effective_from,
                clause_id=e.clause_id,
                heading=e.heading,
                text=e.text,
            )
            for e in excerpts
        ]


def order_fact(order: Order) -> OrderFact:
    return OrderFact(
        id=order.id,
        status=order.status,
        items=[f"{item['quantity']} x {item['name']}" for item in order.items],
        total=order_fact_total(order.total_amount, order.currency),
        shipping_address=order.shipping_address,
        created_at=order.created_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
    )
