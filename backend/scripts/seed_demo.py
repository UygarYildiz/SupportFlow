"""Seed the NovaShop demo data.

Usage (from backend/):
    uv run poe seed            # insert missing demo records (idempotent)
    uv run poe seed --reset    # wipe tickets/orders/customers/users first
"""

import argparse
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.demo.seed import reset_demo_data, seed_demo_data

DEFAULT_DEMO_PASSWORD = "supportflow-demo"  # noqa: S105 - documented demo-only credential


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="delete existing demo data first")
    args = parser.parse_args()

    password = os.environ.get("DEMO_USER_PASSWORD", DEFAULT_DEMO_PASSWORD)
    with Session(get_engine()) as session:
        if args.reset:
            reset_demo_data(session)
        summary = seed_demo_data(session, datetime.now(UTC), password)

    print(
        f"Inserted: {summary.users} users, {summary.customers} customers, "
        f"{summary.orders} orders, {summary.tickets} tickets"
    )
    print("Demo logins: admin@novashop.example (admin), sam@novashop.example (agent_user)")


if __name__ == "__main__":
    main()
