"""SQLAlchemy models for the notifications module.

Cross-module links are foreign keys by identifier only; there are no
relationship() declarations reaching into other modules.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import DispatchStatus, NotificationKind

__all__ = ["Notification", "NotificationDispatch", "NotificationSettings"]

notification_kind_enum = PGEnum(
    NotificationKind,
    name="notification_kind",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)

dispatch_status_enum = PGEnum(
    DispatchStatus,
    name="dispatch_status",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


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


class Notification(Base):
    """The in-app half of every notification (RN-24).

    This row is always written, even when the email fails: the bell is the
    channel the platform actually controls.
    """

    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    kind: Mapped[NotificationKind] = mapped_column(notification_kind_enum, nullable=False)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    body: Mapped[str] = mapped_column(Text(), nullable=False)
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NotificationDispatch(Base):
    """One reminder email, claimed before it is sent (RN-27).

    The unique constraint is the idempotency mechanism, not a safety net: the job
    inserts here with ON CONFLICT DO NOTHING and treats "no row came back" as
    "already sent today, skip". See migration 0008 for the full reasoning.
    """

    __tablename__ = "notification_dispatches"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "task_id",
            "kind",
            "target_date",
            name="uq_notification_dispatches_once",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[NotificationKind] = mapped_column(notification_kind_enum, nullable=False)
    #: The calendar day in Bogotá the reminder belongs to, not the instant it
    #: was sent: that is what makes "twice on the same day" a decidable question.
    target_date: Mapped[date] = mapped_column(Date(), nullable=False)
    status: Mapped[DispatchStatus] = mapped_column(dispatch_status_enum, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(Text(), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text(), nullable=True)
    attempts: Mapped[int] = mapped_column(
        SmallInteger(), nullable=False, server_default=text("1")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
