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


class TicketCategory(StrEnum):
    DELIVERY_DELAY = "delivery_delay"
    REFUND_REQUEST = "refund_request"
    ADDRESS_CHANGE = "address_change"
    DAMAGED_ITEM = "damaged_item"
    GENERAL = "general"
    UNKNOWN = "unknown"


class TicketEventType(StrEnum):
    CREATED = "ticket_created"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ANALYSIS_REQUESTED = "analysis_requested"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"


class AgentRunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


ACTIVE_RUN_STATUSES = frozenset({AgentRunStatus.QUEUED, AgentRunStatus.RUNNING})


class ActorType(StrEnum):
    USER = "user"
    SYSTEM = "system"
    CUSTOMER = "customer"
