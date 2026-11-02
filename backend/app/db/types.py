"""Reusable column types and helpers."""

from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum


def utcnow() -> datetime:
    return datetime.now(UTC)


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Store a StrEnum as VARCHAR + CHECK constraint (no native PG enum).

    Avoids ALTER TYPE migrations when values are added later.
    """
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


TZDateTime = DateTime(timezone=True)
