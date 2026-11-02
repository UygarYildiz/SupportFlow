from typing import Any

from fastapi import APIRouter, status

from app.api.deps import DbSession, StaffUser
from app.schemas.commerce import OrderOut
from app.schemas.common import ErrorResponse
from app.services.orders import OrderService

router = APIRouter(tags=["orders"])

_NOT_FOUND: dict[int | str, dict[str, Any]] = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}


@router.get("/customers/{customer_id}/orders", responses=_NOT_FOUND)
def list_customer_orders(customer_id: str, _: StaffUser, session: DbSession) -> list[OrderOut]:
    orders = OrderService(session).list_customer_orders(customer_id)
    return [OrderOut.model_validate(order) for order in orders]


@router.get("/orders/{order_id}", responses=_NOT_FOUND)
def get_order(order_id: str, _: StaffUser, session: DbSession) -> OrderOut:
    return OrderOut.model_validate(OrderService(session).get_order(order_id))
