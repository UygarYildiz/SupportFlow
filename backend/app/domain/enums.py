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


class ActionType(StrEnum):
    """State-changing actions that always require human approval (docs/REQUIREMENTS.md)."""

    CHANGE_SHIPPING_ADDRESS = "change_shipping_address"
    CREATE_REFUND_REQUEST = "create_refund_request"


ORDER_RELATED_CATEGORIES = frozenset(
    {
        TicketCategory.DELIVERY_DELAY,
        TicketCategory.REFUND_REQUEST,
        TicketCategory.ADDRESS_CHANGE,
        TicketCategory.DAMAGED_ITEM,
    }
)


class TicketEventType(StrEnum):
    CREATED = "ticket_created"
    STATUS_CHANGED = "status_changed"
    PRIORITY_CHANGED = "priority_changed"
    ANALYSIS_REQUESTED = "analysis_requested"
    ANALYSIS_COMPLETED = "analysis_completed"
    ANALYSIS_FAILED = "analysis_failed"
    PROPOSAL_CREATED = "proposal_created"
    PROPOSAL_APPROVED = "proposal_approved"
    PROPOSAL_REJECTED = "proposal_rejected"
    PROPOSAL_EXPIRED = "proposal_expired"
    ACTION_EXECUTED = "action_executed"
    ACTION_FAILED = "action_failed"


class ProposalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTING = "executing"
    EXECUTED = "executed"
    REJECTED = "rejected"
    FAILED = "failed"
    EXPIRED = "expired"


OPEN_PROPOSAL_STATUSES = frozenset(
    {ProposalStatus.PENDING, ProposalStatus.APPROVED, ProposalStatus.EXECUTING}
)


class Decision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class ExecutionOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    REJECTED_BY_PRECHECK = "rejected_by_precheck"


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
