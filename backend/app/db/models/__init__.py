"""Import every model module here so Alembic autogenerate sees all tables."""

from app.db.models.agent_run import AgentRun
from app.db.models.agent_run_step import AgentRunStep
from app.db.models.commerce import Customer, Order
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
    "Order",
    "RefundRequest",
    "Ticket",
    "TicketEvent",
    "User",
]
