"""Calls an MCP server in-process over JSON-RPC, the way the agent and stdio clients do."""

from typing import Any

import anyio
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, Tool


def call_tool(server: MCPServer, name: str, arguments: dict[str, Any]) -> CallToolResult:
    async def call() -> CallToolResult:
        async with Client(server, mode="legacy") as client:
            return await client.call_tool(name, arguments)

    return anyio.run(call)


def list_tools(server: MCPServer) -> list[Tool]:
    async def call() -> list[Tool]:
        async with Client(server, mode="legacy") as client:
            return (await client.list_tools()).tools

    return anyio.run(call)


def error_text(result: CallToolResult) -> str:
    assert result.is_error
    return " ".join(getattr(block, "text", "") for block in result.content)
