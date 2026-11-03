"""MCP contract and the agent's MCP client (Phase 8, ADR-015). No database needed."""

from contextlib import nullcontext
from pathlib import Path
from typing import Any, cast

import anyio
import pytest
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from sqlalchemy.orm import Session

from app.agent.graph import AnalysisError
from app.agent.mcp_tools import McpAgentTools
from app.agent.tools import ToolNotAllowedError
from app.mcp.access import agent_run_authenticator
from app.mcp.server import TOOL_NAMES, build_server
from tests.fakes import InMemoryTools
from tests.mcp_client import list_tools

APP = Path(__file__).resolve().parents[2] / "app"


def _server() -> MCPServer:
    # Listing tools never opens the session.
    return build_server(
        session_scope=lambda: nullcontext(cast(Session, None)),
        authenticate=agent_run_authenticator(1, None),
    )


def test_the_server_offers_only_narrow_read_only_tools() -> None:
    tools = list_tools(_server())

    assert tuple(t.name for t in tools) == TOOL_NAMES
    for tool in tools:
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is True
        assert tool.annotations.destructive_hint is False
        assert "ticket_id" in tool.input_schema["required"]
        assert tool.output_schema is not None  # structured, schema-checked results
    limits = {t.name: t.input_schema["properties"].get("limit") for t in tools}
    assert limits["get_customer_orders"]["maximum"] == 20
    assert limits["get_ticket_history"]["maximum"] == 10


def test_mcp_code_has_no_write_path() -> None:
    """Import boundary: the adapter can't reach execution, approval or order writes."""
    forbidden = ("app.integrations", "ProposalService", "MockOrderSystem", ".decide(", "executor")
    for source in (APP / "mcp").rglob("*.py"):
        content = source.read_text(encoding="utf-8")
        for name in forbidden:
            assert name not in content, f"{source.name} references {name}"


def test_domain_and_services_do_not_depend_on_mcp() -> None:
    for package in ("domain", "services"):
        for source in (APP / package).rglob("*.py"):
            content = source.read_text(encoding="utf-8")
            assert "import mcp" not in content
            assert "from mcp" not in content
            assert "app.mcp" not in content, f"{source.name} imports app.mcp"


# --- the agent's client side ----------------------------------------------------------


def _stub(**tools: Any) -> MCPServer:
    """A stand-in server with hand-written tools, to drive the client's error handling."""
    server = MCPServer("stub")
    for name, fn in tools.items():
        server.add_tool(fn, name=name, structured_output=True)
    return server


def _agent_tools(server: MCPServer, timeout: float = 5.0) -> McpAgentTools:
    return McpAgentTools(local=InMemoryTools(), server=server, ticket_id=1, timeout_seconds=timeout)


def test_not_found_and_malformed_ids_read_as_missing_orders() -> None:
    def get_order_status(ticket_id: int, order_id: str) -> dict[str, Any]:
        raise ToolError(f"[not_found] Sipariş bulunamadı: {order_id}")

    tools = _agent_tools(_stub(get_order_status=get_order_status))

    assert tools.call("get_order", order_id="ORD-404") is None
    assert tools.calls[-1].found is False
    assert tools.calls[-1].via == "mcp"


@pytest.mark.parametrize("code", ["forbidden", "unauthorized", "internal_error"])
def test_other_tool_errors_stop_the_analysis(code: str) -> None:
    """A refused or broken lookup is not 'no orders': that would mislead the draft."""

    def get_customer_orders(ticket_id: int, limit: int = 10) -> dict[str, Any]:
        raise ToolError(f"[{code}] nope")

    tools = _agent_tools(_stub(get_customer_orders=get_customer_orders))

    with pytest.raises(AnalysisError) as raised:
        tools.call("get_customer_orders", limit=10)
    assert raised.value.code == "tool_error"
    assert code in str(raised.value)


def test_a_slow_tool_times_out() -> None:
    async def get_customer_orders(ticket_id: int, limit: int = 10) -> dict[str, Any]:
        await anyio.sleep(5)
        return {"orders": []}

    tools = _agent_tools(_stub(get_customer_orders=get_customer_orders), timeout=0.2)

    with pytest.raises(AnalysisError) as raised:
        tools.call("get_customer_orders", limit=10)
    assert raised.value.code == "tool_timeout"


def test_results_are_checked_against_the_response_schema() -> None:
    def get_order_status(ticket_id: int, order_id: str) -> dict[str, Any]:
        return {"id": order_id, "status": "teleported"}  # not an order

    tools = _agent_tools(_stub(get_order_status=get_order_status))

    with pytest.raises(AnalysisError) as raised:
        tools.call("get_order", order_id="ORD-1")
    assert raised.value.code == "tool_error"


def test_history_is_only_for_the_runs_own_ticket() -> None:
    tools = _agent_tools(_stub())

    with pytest.raises(ToolNotAllowedError):
        tools.call("get_customer_tickets", exclude_ticket_id=2, limit=5)
    with pytest.raises(ToolNotAllowedError):
        tools.call("update_order", order_id="ORD-1")


def test_rule_tools_stay_direct_calls() -> None:
    local = InMemoryTools()
    tools = McpAgentTools(local=local, server=_stub(), ticket_id=1, timeout_seconds=1)

    assert tools.call("get_policy", policy="return", order_id="ORD-1") is None
    assert [(c.name, c.via) for c in tools.calls] == [("get_policy", "direct")]
