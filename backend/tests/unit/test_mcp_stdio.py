"""The stdio entry point really speaks MCP (what MCP Inspector and other hosts launch).

No database needed: listing tools doesn't touch it, and a bad token is refused before
any query.
"""

import os
import subprocess
import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, Tool

from app.agent.mcp_tools import error_code
from app.mcp.server import TOOL_NAMES

BACKEND = Path(__file__).resolve().parents[2]


def _env(token: str) -> dict[str, str]:
    # An explicit (possibly empty) value wins over a token in the developer's .env.
    return os.environ | {"MCP_ACCESS_TOKEN": token, "PYTHONPATH": str(BACKEND)}


def test_stdio_server_lists_its_tools_and_refuses_a_bad_token() -> None:
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "app.mcp"], env=_env("not-a-token"), cwd=BACKEND
    )

    async def session() -> tuple[list[Tool], CallToolResult]:
        async with Client(params, mode="legacy", read_timeout_seconds=30) as client:
            tools = (await client.list_tools()).tools
            result = await client.call_tool(
                "get_order_status", {"ticket_id": 1, "order_id": "ORD-1"}
            )
            return tools, result

    tools, result = anyio.run(session)

    assert tuple(t.name for t in tools) == TOOL_NAMES
    assert error_code(result) == "unauthorized"


def test_stdio_server_does_not_start_without_a_token() -> None:
    finished = subprocess.run(
        [sys.executable, "-m", "app.mcp"],
        cwd=BACKEND,
        env=_env(""),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert finished.returncode == 2
    assert "MCP_ACCESS_TOKEN" in finished.stderr
    assert finished.stdout == ""  # stdout belongs to the protocol
