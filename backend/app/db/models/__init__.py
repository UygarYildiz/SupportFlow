"""Import every model module here so Alembic autogenerate sees all tables."""

from app.db.models.agent_run import AgentRun
from app.db.models.agent_run_step import AgentRunStep
from app.db.models.commerce import Customer, Order
from app.db.models.installation import Installation
from app.db.models.knowledge import IngestionJob, PolicyChunk, PolicyDocument
from app.db.models.proposal import ActionExecution, ActionProposal, AuditLog, RefundRequest
from app.db.models.ticket import Ticket, TicketEvent
from app.db.models.user import User

__all__ = [
    "ActionExecution",
    "ActionProposal",
    "AgentRun",
    "AgentRunStep",
    "AuditLog",
    "Customer",
    "IngestionJob",
    "Installation",
    "Order",
    "PolicyChunk",
    "PolicyDocument",
    "RefundRequest",
    "Ticket",
    "TicketEvent",
    "User",
]
