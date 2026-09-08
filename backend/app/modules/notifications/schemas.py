"""Pydantic schemas for the notifications module (api-contract.md 7 and 9)."""

import datetime
import uuid

from pydantic import BaseModel, Field

from app.core.enums import NotificationKind


class NotificationRead(BaseModel):
    id: uuid.UUID
    kind: NotificationKind
    title: str
    body: str
    task_id: uuid.UUID | None
    project_id: uuid.UUID | None
    read_at: datetime.datetime | None
    created_at: datetime.datetime


class NotificationsPage(BaseModel):
    items: list[NotificationRead]
    total: int
    page: int
    size: int


class UnreadCount(BaseModel):
    """The shape the bell polls every 60 seconds (api-contract.md 7)."""

    unread: int


class MarkAllReadResult(BaseModel):
    marked: int


class NotificationSettingsRead(BaseModel):
    reminder_days_before: list[int]
    send_hour: int
    timezone: str
    overdue_enabled: bool
    updated_at: datetime.datetime
    updated_by: uuid.UUID | None


class NotificationSettingsUpdate(BaseModel):
    """RN-26. The bounds are repeated in the service, which is what answers with
    a message in Spanish naming the offending rule; these are the cheap first
    line so an obviously wrong body never reaches it.

    ``timezone`` is deliberately absent: RN-26 fixes it at America/Bogota.
    """

    reminder_days_before: list[int] = Field(min_length=0, max_length=5)
    send_hour: int = Field(ge=0, le=23)
    overdue_enabled: bool


class ReminderJobSummary(BaseModel):
    """What POST /internal/jobs/reminders answers (api-contract.md 9)."""

    executed_at: datetime.datetime
    due_soon_sent: int
    overdue_sent: int
    skipped_duplicates: int
    failures: int
