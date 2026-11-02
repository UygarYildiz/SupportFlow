from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.domain.enums import OrderStatus
from app.schemas.common import ApiModel


class OrderItem(BaseModel):
    sku: str
    name: str
    quantity: int
    unit_price: Decimal


class OrderOut(ApiModel):
    id: str
    customer_id: str
    status: OrderStatus
    total_amount: Decimal
    currency: str
    shipping_address: str
    items: list[OrderItem]
    created_at: datetime
    shipped_at: datetime | None
    delivered_at: datetime | None


class CustomerSummary(ApiModel):
    id: str
    display_name: str
    email: str
