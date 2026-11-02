"""Mock order/finance system that executes approved actions.

Stands in for an external system (shop backend, payment provider). It behaves
like a well-designed external API should:
- idempotent by key: repeating a request returns the first result, never a second effect;
- re-validates the current order state right before changing it (time-of-check vs
  time-of-use: the order may have shipped since the proposal was made).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActionExecution, Order, RefundRequest
from app.domain import policies
from app.domain.enums import ActionType, ExecutionOutcome
from app.domain.errors import NotFoundError


@dataclass(frozen=True)
class ActionRequest:
    proposal_id: int
    action_type: ActionType
    customer_id: str
    order_id: str
    payload: dict[str, Any]
    policy_rule: str
    idempotency_key: str
    actor_id: int | None


@dataclass(frozen=True)
class ActionResult:
    outcome: ExecutionOutcome
    external_ref: str | None
    detail: dict[str, Any]
    replayed: bool = False  # True when the key was seen before and nothing new happened


class MockOrderSystem:
    def __init__(self, session: Session, clock: Callable[[], datetime]) -> None:
        self.session = session
        self.clock = clock

    def apply(self, request: ActionRequest) -> ActionResult:
        previous = self.session.scalar(
            select(ActionExecution).where(
                ActionExecution.idempotency_key == request.idempotency_key
            )
        )
        if previous is not None:
            return ActionResult(
                previous.outcome, previous.external_ref, previous.detail, replayed=True
            )

        # Lock the order: no concurrent change between the re-check and the update.
        order = self.session.scalar(
            select(Order)
            .where(Order.id == request.order_id, Order.customer_id == request.customer_id)
            .with_for_update()
        )
        if order is None:
            raise NotFoundError("Order", request.order_id)

        decision = self._recheck(request, order)
        if not decision.allowed:
            result = ActionResult(
                ExecutionOutcome.REJECTED_BY_PRECHECK,
                None,
                {"rule": decision.rule, "reason": decision.reason},
            )
        elif request.action_type == ActionType.CHANGE_SHIPPING_ADDRESS:
            order.shipping_address = request.payload["new_address"]
            result = ActionResult(
                ExecutionOutcome.SUCCEEDED, order.id, {"field": "shipping_address"}
            )
        else:
            refund = RefundRequest(
                proposal_id=request.proposal_id,
                order_id=order.id,
                amount=order.total_amount,
                currency=order.currency,
                reason=str(request.payload.get("refund_reason", "unspecified")),
            )
            self.session.add(refund)
            self.session.flush()
            result = ActionResult(
                ExecutionOutcome.SUCCEEDED, f"REF-{refund.id}", {"amount": str(refund.amount)}
            )

        self.session.add(
            ActionExecution(
                proposal_id=request.proposal_id,
                idempotency_key=request.idempotency_key,
                outcome=result.outcome,
                external_ref=result.external_ref,
                detail=result.detail,
                executed_by=request.actor_id,
            )
        )
        self.session.flush()
        return result

    def _recheck(self, request: ActionRequest, order: Order) -> policies.PolicyDecision:
        now = self.clock()
        if request.action_type == ActionType.CHANGE_SHIPPING_ADDRESS:
            return policies.check_address_change(order.status)
        if request.payload.get("refund_reason") == "damaged_item":
            return policies.check_damage_report(order.delivered_at, now)
        return policies.check_return_request(order.delivered_at, now)
