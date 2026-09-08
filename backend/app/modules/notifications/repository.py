"""Data access for notifications, dispatches and the global settings row.

Queries only, no decisions. The one method worth reading twice is
``claim_dispatch``: it is not a query that reports something, it is a query that
*takes* something — the right to send one email — and the unique constraint is
the referee.
"""

import datetime
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DispatchStatus, NotificationKind
from app.modules.notifications.models import (
    Notification,
    NotificationDispatch,
    NotificationSettings,
)

SETTINGS_ID = 1


class NotificationsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, obj: object) -> None:
        self.db.add(obj)

    # --- Settings ---

    async def get_settings(self) -> NotificationSettings | None:
        return await self.db.get(NotificationSettings, SETTINGS_ID)

    # --- Inbox ---

    async def list_for_user(
        self, user_id: uuid.UUID, *, unread_only: bool, limit: int, offset: int
    ) -> list[Notification]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)
        rows = await self.db.execute(query)
        return list(rows.scalars().all())

    async def count_for_user(self, user_id: uuid.UUID, *, unread_only: bool) -> int:
        query = select(func.count()).select_from(Notification).where(
            Notification.user_id == user_id
        )
        if unread_only:
            query = query.where(Notification.read_at.is_(None))
        return (await self.db.execute(query)).scalar_one()

    async def get_for_user(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification | None:
        """Scoped by owner on purpose: somebody else's notification has to read
        as missing, not as forbidden."""
        rows = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        return rows.scalar_one_or_none()

    async def mark_all_read(self, user_id: uuid.UUID, *, when: datetime.datetime) -> int:
        """One statement rather than a read followed by N writes. Already-read
        rows are left alone so their original timestamp survives."""
        result = await self.db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=when)
        )
        return result.rowcount or 0

    # --- Dispatches ---

    async def claim_dispatch(
        self,
        *,
        user_id: uuid.UUID,
        task_id: uuid.UUID | None,
        kind: NotificationKind,
        target_date: datetime.date,
    ) -> uuid.UUID | None:
        """Claim the right to send one reminder. Returns None if it is taken.

        ``ON CONFLICT DO NOTHING ... RETURNING id`` is the whole idempotency
        mechanism (RN-27). No row comes back when the unique constraint already
        holds a claim for this (user, task, kind, day), and that is the signal to
        skip — decided by PostgreSQL, atomically, instead of by a read-then-write
        in Python that two concurrent runs of the job could both pass.

        The row is written as SENT before anything is sent, because the claim has
        to exist even if the process dies mid-send: a reminder that went missing
        is a smaller problem than one delivered twice a minute apart.
        """
        statement = (
            insert(NotificationDispatch)
            .values(
                user_id=user_id,
                task_id=task_id,
                kind=kind,
                target_date=target_date,
                status=DispatchStatus.SENT,
            )
            .on_conflict_do_nothing(constraint="uq_notification_dispatches_once")
            .returning(NotificationDispatch.id)
        )
        return (await self.db.execute(statement)).scalar_one_or_none()

    async def mark_dispatch_failed(
        self, dispatch_id: uuid.UUID, *, error: str | None, attempts: int
    ) -> None:
        await self.db.execute(
            update(NotificationDispatch)
            .where(NotificationDispatch.id == dispatch_id)
            .values(
                status=DispatchStatus.FAILED,
                error_message=(error or "")[:2000] or None,
                attempts=attempts,
            )
        )

    async def mark_dispatch_sent(
        self, dispatch_id: uuid.UUID, *, provider_message_id: str | None, attempts: int
    ) -> None:
        await self.db.execute(
            update(NotificationDispatch)
            .where(NotificationDispatch.id == dispatch_id)
            .values(provider_message_id=provider_message_id, attempts=max(attempts, 1))
        )
