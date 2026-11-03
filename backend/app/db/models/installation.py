from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import TZDateTime, utcnow


class Installation(Base):
    """The one business this self-hosted installation serves (ADR-017).

    At most one row: the primary key is pinned to 1, so two concurrent first-run
    setups cannot both succeed (the second insert violates the primary key).
    """

    __tablename__ = "installation"
    __table_args__ = (CheckConstraint("id = 1", name="single_row"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False, default=1)
    organization_name: Mapped[str] = mapped_column(String(120))
    completed_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    completed_at: Mapped[datetime] = mapped_column(TZDateTime, default=utcnow)
