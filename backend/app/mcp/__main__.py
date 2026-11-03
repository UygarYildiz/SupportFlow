"""stdio entry point: `uv run poe mcp` (or `python -m app.mcp`).

The client (an MCP host such as MCP Inspector or Claude Desktop) starts this process
and talks JSON-RPC over stdin/stdout, so nothing else may be printed to stdout: logs
go to stderr. The caller's identity is the staff access token in `MCP_ACCESS_TOKEN`.
"""

import logging
import sys

from app.core.config import get_settings
from app.db.session import session_scope
from app.mcp.access import staff_token_authenticator
from app.mcp.server import build_server


def main() -> int:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level, stream=sys.stderr)
    if settings.mcp_access_token is None or not settings.mcp_access_token.get_secret_value():
        print(
            "MCP_ACCESS_TOKEN is not set. Create one with `uv run poe mcp-token` "
            "(see docs/OPERATIONS.md).",
            file=sys.stderr,
        )
        return 2
    server = build_server(
        session_scope=session_scope,
        authenticate=staff_token_authenticator(settings.mcp_access_token, settings),
    )
    server.run("stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
