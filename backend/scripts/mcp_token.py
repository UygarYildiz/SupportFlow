"""Print a staff access token for the stdio MCP server (ADR-015).

Usage (from backend/):
    uv run poe mcp-token --email selin@novashop.example

The password is read from MCP_LOGIN_PASSWORD or asked for. The token is an ordinary
access token (ACCESS_TOKEN_EXPIRE_MINUTES); the MCP server verifies it and re-reads
the user on every tool call. Put it in MCP_ACCESS_TOKEN of the MCP client's config.
"""

import argparse
import getpass
import os
import sys

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.session import session_scope
from app.services.users import UserService


def main() -> int:
    parser = argparse.ArgumentParser(description="Print a staff access token for the MCP server")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    password = os.environ.get("MCP_LOGIN_PASSWORD") or getpass.getpass("Password: ")
    settings = get_settings()
    with session_scope() as session:
        user = UserService(session).authenticate(args.email, password)
        if user is None:
            print("E-posta ya da parola hatalı", file=sys.stderr)
            return 1
        print(create_access_token(user.id, user.role, settings))
    print(f"Valid for {settings.access_token_expire_minutes} minutes.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
