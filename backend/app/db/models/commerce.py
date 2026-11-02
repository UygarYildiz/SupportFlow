"""Mock CRM / order data. IDs mirror an external system (e.g. CUS-0001, ORD-1001)."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import TZDateTime, str_enum, utcnow
from app.domain.enums import OrderStatus


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(254), unique=True)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)

    orders: Mapped[list["Order"]] = relationship(back_populates="customer")


class Order(Base):
    __tablename__ = "orders"
    # Target for the composite FK on tickets: guarantees a ticket's order
    # belongs to the ticket's customer at the database level.
    __table_args__ = (UniqueConstraint("id", "customer_id", name="uq_orders_id_customer_id"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(str_enum(OrderStatus, "order_status"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3))
    shipping_address: Mapped[str] = mapped_column(Text)
    # [{"sku": "...", "name": "...", "quantity": 1, "unit_price": "19.90"}]
    items: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
    shipped_at: Mapped[datetime | None] = mapped_column(TZDateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(TZDateTime)

    customer: Mapped[Customer] = relationship(back_populates="orders")
