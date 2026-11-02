"""Enumerations shared by the domain, persistence and API layers."""

from enum import StrEnum


class UserRole(StrEnum):
    AGENT_USER = "agent_user"
    ADMIN = "admin"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class TicketStatus(StrEnum):
    NEW = "new"
    TRIAGING = "triaging"
    AWAITING_REVIEW = "awaiting_review"
    NEEDS_INFO = "needs_info"
    RESOLVED = "resolved"
    FAILED = "failed"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketEventType(StrEnum):
    CREATED = "ticket_created"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"


class ActorType(StrEnum):
    USER = "user"
    SYSTEM = "system"
    CUSTOMER = "customer"
