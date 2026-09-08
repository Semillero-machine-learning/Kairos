"""Business rules for notifications (RN-24 to RN-30).

This service and its repository **import nothing from any other module**
(architecture.md 2): they receive everything they need as primitives and
dataclasses. That is what lets notifications be the sink where every other module
and the scheduled job converge without becoming the knot where they all tangle.
Whoever calls ``deliver`` has already decided that the recipient is active and
that the project is not archived; this service decides only how the message is
written down and sent. (The routers annotate ``User`` for the shared
``get_current_user`` dependency, like every other router in the application; the
rule is about data access, and no query here crosses a module.)

Two paths, and the difference between them is the point:

* ``deliver`` — the immediate notifications (assignment, review). Writes the
  in-app row, commits, then sends. No dispatch row: those exist to answer "did
  this reminder already go out today", and an assignment is not a reminder. A
  second assignment on the same day is a second real event and has to arrive.
* ``deliver_reminder`` — the scheduled ones. Claims the dispatch row **first**
  (RN-27), and a taken claim means the work was already done.

Both share one promise from RN-30 and CLAUDE.md rule 9: a mail failure is logged
and the business operation carries on. Neither ever raises because of the
provider.
"""

import datetime
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now_utc
from app.core.config import get_settings
from app.core.enums import NotificationKind
from app.core.exceptions import NotFoundError, ValidationError
from app.core.pagination import Pagination
from app.integrations.email import EmailClient, EmailResult, render_email
from app.modules.notifications.models import Notification, NotificationSettings
from app.modules.notifications.repository import NotificationsRepository

logger = logging.getLogger("kairos.notifications")

MAX_REMINDER_DAYS = 5
MAX_DAYS_AHEAD = 30


@dataclass(frozen=True)
class Recipient:
    """Who to write to, handed in by the caller.

    A copy of three fields rather than a ``User``: this module must not depend on
    the users module, and it has no business holding anything else about a
    person.
    """

    user_id: uuid.UUID
    email: str
    full_name: str


@dataclass(frozen=True)
class NotificationContent:
    """What to say, in both channels at once.

    The in-app text and the email body are written together on purpose: they are
    the same message and drifting apart would be a bug nobody notices, because
    almost nobody reads both.
    """

    kind: NotificationKind
    title: str
    body: str
    #: Extra line the email carries and the bell does not: there is room for it
    #: there, and it is usually the deadline or the reviewer's comment.
    detail: str | None = None
    task_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None
    project_name: str | None = None
    #: Deep link into the app, so the email is one click from the task.
    link_path: str | None = None


@dataclass(frozen=True)
class DeliveryOutcome:
    """What happened, for the job's summary (api-contract.md 9)."""

    sent: bool = False
    skipped_duplicate: bool = False
    failed: bool = False


class NotificationsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = NotificationsRepository(db)
        self.email = EmailClient()

    # --- Settings (RF-43, RN-26) ---

    async def get_settings(self) -> NotificationSettings:
        settings = await self.repo.get_settings()
        if settings is None:
            # Seeded by migration 0003. Missing means the database was not
            # migrated, and saying so beats a confusing None downstream.
            raise NotFoundError("No hay configuración de notificaciones.")
        return settings

    async def update_settings(
        self,
        *,
        reminder_days_before: list[int],
        send_hour: int,
        overdue_enabled: bool,
        updated_by: uuid.UUID,
    ) -> NotificationSettings:
        """Change the platform-wide reminder configuration (RN-26).

        The timezone is not a parameter: RN-26 pins it to America/Bogota, and
        making it editable would let one setting change quietly move every
        deadline in the platform.
        """
        days = self._validate_days(reminder_days_before)
        if not 0 <= send_hour <= 23:
            raise ValidationError("La hora de envío debe estar entre 0 y 23.")

        settings = await self.get_settings()
        settings.reminder_days_before = days
        settings.send_hour = send_hour
        settings.overdue_enabled = overdue_enabled
        settings.updated_by = updated_by
        settings.updated_at = now_utc()
        await self.db.commit()
        return settings

    @staticmethod
    def _validate_days(days: list[int]) -> list[int]:
        """At most 5 values, each between 0 and 30, no repeats (api-contract.md 7)."""
        if len(days) > MAX_REMINDER_DAYS:
            raise ValidationError(
                f"Se admiten como máximo {MAX_REMINDER_DAYS} días de aviso previo."
            )
        if any(day < 0 or day > MAX_DAYS_AHEAD for day in days):
            raise ValidationError(
                f"Cada día de aviso debe estar entre 0 y {MAX_DAYS_AHEAD}."
            )
        if len(set(days)) != len(days):
            raise ValidationError("Los días de aviso no se pueden repetir.")
        # Furthest away first, which is the order they will fire in.
        return sorted(days, reverse=True)

    # --- Inbox (RF-38) ---

    async def list_inbox(
        self, user_id: uuid.UUID, *, unread_only: bool, pagination: Pagination
    ) -> tuple[list[Notification], int]:
        items = await self.repo.list_for_user(
            user_id,
            unread_only=unread_only,
            limit=pagination.limit,
            offset=pagination.offset,
        )
        total = await self.repo.count_for_user(user_id, unread_only=unread_only)
        return items, total

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.count_for_user(user_id, unread_only=True)

    async def mark_read(
        self, notification_id: uuid.UUID, user_id: uuid.UUID
    ) -> Notification:
        notification = await self.repo.get_for_user(notification_id, user_id)
        if notification is None:
            # Someone else's notification reads as missing, never as forbidden.
            raise NotFoundError("Notificación no encontrada.")
        if notification.read_at is None:
            notification.read_at = now_utc()
            await self.db.commit()
        return notification

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        marked = await self.repo.mark_all_read(user_id, when=now_utc())
        await self.db.commit()
        return marked

    # --- Delivery ---

    async def deliver(
        self, recipient: Recipient, content: NotificationContent
    ) -> DeliveryOutcome:
        """An immediate notification: bell first, then email (RN-24).

        Never raises. The caller has already committed a business operation and
        RN-30 is explicit that no mail failure may undo it.
        """
        self._record(recipient, content)
        await self.db.commit()
        result = await self._send_email(recipient, content)
        return DeliveryOutcome(sent=result.success, failed=not result.success)

    async def deliver_reminder(
        self,
        recipient: Recipient,
        content: NotificationContent,
        *,
        target_date: datetime.date,
    ) -> DeliveryOutcome:
        """A scheduled reminder, sent at most once per person, task and day.

        The order is what makes this idempotent and it is not negotiable
        (CLAUDE.md rule 5): claim the dispatch row, and only then write and send.
        If the claim fails the email already went out today and there is nothing
        left to do.
        """
        dispatch_id = await self.repo.claim_dispatch(
            user_id=recipient.user_id,
            task_id=content.task_id,
            kind=content.kind,
            target_date=target_date,
        )
        if dispatch_id is None:
            # Nothing to undo: ON CONFLICT DO NOTHING wrote no row and left the
            # transaction perfectly healthy. A rollback here would throw away
            # whatever the caller had already staged.
            return DeliveryOutcome(skipped_duplicate=True)

        self._record(recipient, content)
        # Committed before the send so the claim is visible to any concurrent
        # run immediately, rather than at the end of a network round trip.
        await self.db.commit()

        result = await self._send_email(recipient, content)
        if result.success:
            await self.repo.mark_dispatch_sent(
                dispatch_id,
                provider_message_id=result.provider_message_id,
                attempts=result.attempts,
            )
        else:
            await self.repo.mark_dispatch_failed(
                dispatch_id, error=result.error, attempts=result.attempts
            )
        await self.db.commit()
        return DeliveryOutcome(sent=result.success, failed=not result.success)

    def _record(self, recipient: Recipient, content: NotificationContent) -> None:
        """The in-app row, written for every notification without exception.

        RN-24 and the "Fallo del proveedor de correo" scenario of HU-10 both say
        the same thing from different angles: the bell is the channel the
        platform controls, so it is never conditional on the email.
        """
        self.repo.add(
            Notification(
                user_id=recipient.user_id,
                kind=content.kind,
                title=content.title,
                body=content.body,
                task_id=content.task_id,
                project_id=content.project_id,
            )
        )

    async def _send_email(
        self, recipient: Recipient, content: NotificationContent
    ) -> EmailResult:
        """The email half. The three retries live in the client (RN-30); a
        failure is logged here and never propagates."""
        base_url = get_settings().frontend_url.rstrip("/")
        html = render_email(
            "notification.html",
            full_name=recipient.full_name,
            title=content.title,
            body=content.body,
            detail=content.detail,
            project_name=content.project_name,
            action_url=f"{base_url}{content.link_path}" if content.link_path else None,
        )
        result = await self.email.send(
            to=recipient.email, subject=content.title, html=html
        )
        if not result.success:
            logger.warning(
                "Notificación %s registrada pero no enviada a %s: %s",
                content.kind,
                recipient.email,
                result.error,
            )
        return result
