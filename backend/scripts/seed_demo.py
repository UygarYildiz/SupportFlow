"""Seed the NovaShop demo data.

Usage (from backend/):
    uv run poe seed            # insert missing demo records (idempotent)
    uv run poe seed --reset    # wipe tickets/orders/customers/users first

Besides the records, a few tickets are analyzed with the fake LLM (never a paid
API) and one proposal is approved, so the dashboard and approval queue open
with something to show. Pass --no-activity to skip that.
"""

import argparse
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.demo.activity import seed_demo_activity
from app.demo.seed import reset_demo_data, seed_demo_data

DEFAULT_DEMO_PASSWORD = "supportflow-demo"  # noqa: S105 - documented demo-only credential


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="delete existing demo data first")
    parser.add_argument(
        "--no-activity", action="store_true", help="skip the pre-analyzed demo tickets"
    )
    args = parser.parse_args()

    password = os.environ.get("DEMO_USER_PASSWORD", DEFAULT_DEMO_PASSWORD)
    with Session(get_engine()) as session:
        if args.reset:
            reset_demo_data(session)
        summary = seed_demo_data(session, datetime.now(UTC), password)
        activity = None
        if not args.no_activity:
            activity = seed_demo_activity(session, lambda: datetime.now(UTC))

    print(
        f"Inserted: {summary.users} users, {summary.customers} customers, "
        f"{summary.orders} orders, {summary.tickets} tickets"
    )
    if activity is not None:
        print(f"Demo activity: {activity.analyzed} tickets analyzed, {activity.approved} approved")
    print("Demo logins: admin@novashop.example (admin), selin@novashop.example (agent_user)")


if __name__ == "__main__":
    main()
