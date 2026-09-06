"""SQLAlchemy models for the notifications module.

Cross-module links are foreign keys by identifier only; there are no
relationship() declarations reaching into other modules.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationSettings(Base):
    """Single global row (RF-43): id is pinned to 1 by a CHECK constraint."""

    __tablename__ = "notification_settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_notification_settings_singleton"),
        CheckConstraint("send_hour BETWEEN 0 AND 23", name="ck_notification_settings_send_hour"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=False)
    reminder_days_before: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, server_default=text("'{3,1,0}'")
    )
    send_hour: Mapped[int] = mapped_column(nullable=False, server_default=text("7"))
    timezone: Mapped[str] = mapped_column(
        nullable=False, server_default=text("'America/Bogota'")
    )
    overdue_enabled: Mapped[bool] = mapped_column(
        nullable=False, server_default=text("true")
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
