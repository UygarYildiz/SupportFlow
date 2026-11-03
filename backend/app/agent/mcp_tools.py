"""Agent tools over MCP (Phase 8, ADR-015).

Order and ticket-history lookups go through SupportFlow's own MCP server, connected
in-process: the same JSON-RPC messages, schemas, access checks and error codes an
external MCP client gets. The connection's identity is this run, bound to its one
ticket (`AgentRunPrincipal`), so a wrong `ticket_id` is refused by the server, not
trusted by the client. Policy checks and policy search stay direct calls: they are
deterministic rule code and the knowledge base, not customer data.

Tool results are data. They are validated against the server's response schemas
and reach the model only inside the neutralized `<facts>` block.
"""

import asyncio
import re
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

import anyio
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from app.agent.graph import AnalysisError
from app.agent.schemas import OrderFact, PreviousTicketFact, order_fact_total
from app.agent.tools import ALLOWED_TOOLS, AgentTools, ToolCall, ToolNotAllowedError
from app.mcp.schemas import CustomerOrdersOut, OrderStatusOut, TicketHistoryOut
from app.mcp.server import ERROR_CODES

# Agent tool name -> MCP tool name. Everything else stays a direct call.
MCP_TOOLS = {
    "get_order": "get_order_status",
    "get_customer_orders": "get_customer_orders",
    "get_customer_tickets": "get_ticket_history",
}

_ERROR_CODE = re.compile(r"^(?:Error executing tool [\w-]+: )?\[([a-z_]+)\] ")


@dataclass
class McpAgentTools:
    """`AgentTools` whose customer-data lookups are MCP tool calls."""

    local: AgentTools  # get_policy and search_policies (DatabaseTools in production)
    server: MCPServer
    ticket_id: int
    timeout_seconds: float
    calls: list[ToolCall] = field(default_factory=list)

    def call(self, name: str, **arguments: Any) -> Any:
        if name not in ALLOWED_TOOLS:
            raise ToolNotAllowedError(f"Tool '{name}' is not allowed")
        if name not in MCP_TOOLS:
            result = self.local.call(name, **arguments)
            self.calls.append(self.local.calls[-1])
            return result
        try:
            result = getattr(self, f"_{name}")(**arguments)
        except ValidationError:  # the result does not match the server's response schema
            raise AnalysisError(
                "tool_error", f"Sipariş aracı geçersiz yanıt verdi ({name})"
            ) from None
        found = result is not None and result != []
        self.calls.append(ToolCall(name=name, arguments=arguments, found=found, via="mcp"))
        return result

    def _get_order(self, order_id: str) -> OrderFact | None:
        data = self._call("get_order_status", {"ticket_id": self.ticket_id, "order_id": order_id})
        return None if data is None else _order_fact(OrderStatusOut.model_validate(data))

    def _get_customer_orders(self, limit: int = 10) -> list[OrderFact]:
        data = self._call("get_customer_orders", {"ticket_id": self.ticket_id, "limit": limit})
        if data is None:
            return []
        return [_order_fact(order) for order in CustomerOrdersOut.model_validate(data).orders]

    def _get_customer_tickets(
        self, exclude_ticket_id: int, limit: int = 5
    ) -> list[PreviousTicketFact]:
        if exclude_ticket_id != self.ticket_id:  # the server always excludes its own ticket
            raise ToolNotAllowedError("Ticket history is only available for the run's ticket")
        data = self._call("get_ticket_history", {"ticket_id": self.ticket_id, "limit": limit})
        if data is None:
            return []
        return [
            PreviousTicketFact(id=t.id, subject=t.subject, status=t.status, created_at=t.created_at)
            for t in TicketHistoryOut.model_validate(data).tickets
        ]

    def _call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any] | None:
        """The tool's structured result, or None when the server says `not_found`."""

        async def call() -> CallToolResult:
            with anyio.fail_after(self.timeout_seconds):
                async with Client(
                    self.server, mode="legacy", read_timeout_seconds=self.timeout_seconds
                ) as client:
                    return await client.call_tool(tool, arguments)

        try:
            result = _run_blocking(call)
        except TimeoutError:
            raise AnalysisError(
                "tool_timeout", f"Sipariş aracı zamanında yanıt vermedi ({tool})"
            ) from None
        if result.is_error:
            code = error_code(result)
            # A malformed order ID cannot name an existing order: same as not found.
            if code == "not_found" or (code == "invalid_arguments" and tool == "get_order_status"):
                return None
            raise AnalysisError("tool_error", f"Sipariş aracı hata verdi ({tool}: {code})")
        if result.structured_content is None:
            raise AnalysisError("tool_error", f"Sipariş aracı boş yanıt verdi ({tool})")
        return result.structured_content


def error_code(result: CallToolResult) -> str:
    """The server's error code (`app.mcp.server.ERROR_CODES`); anything else is the SDK
    rejecting the arguments against the tool's input schema."""
    text = next((c.text for c in result.content if isinstance(c, TextContent)), "")
    match = _ERROR_CODE.match(text)
    if match and match.group(1) in ERROR_CODES:
        return match.group(1)
    return "invalid_arguments"


def _order_fact(order: OrderStatusOut) -> OrderFact:
    return OrderFact(
        id=order.id,
        status=order.status,
        items=[f"{item.quantity} x {item.name}" for item in order.items],
        total=order_fact_total(order.total_amount, order.currency),
        shipping_address=order.shipping_address,
        created_at=order.created_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
    )


def _run_blocking[T](fn: Callable[[], Awaitable[T]]) -> T:
    """Run an async MCP exchange from the graph's synchronous code."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return anyio.run(fn)
    with ThreadPoolExecutor(max_workers=1) as pool:  # called from inside an event loop
        return pool.submit(anyio.run, fn).result()
