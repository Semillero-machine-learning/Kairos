"""The scheduled reminder job (RF-40, RF-41, RF-44, RN-27 to RN-29).

This file is the orchestrator, and that is why it lives outside ``modules/``. It
is the one place allowed to hold three module services at once: it asks ``tasks``
which deadlines are near, ``projects`` which of those projects are still active
and who can review them, ``users`` who is still active, and hands the result to
``notifications``, which looks nothing up on its own (architecture.md 2).

The algorithm is architecture.md 4, transcribed. Two properties are worth stating
because they are easy to break by "improving" this file:

* **Idempotent by construction (RN-27).** Every send goes through
  ``deliver_reminder``, which claims a row in ``notification_dispatches`` before
  it sends. Running the job twice in a row sends nothing the second time. There
  is no check in this file that compares against what was already sent, and
  adding one would be strictly worse: it would race.
* **No catching up (RN-29).** Everything is computed against *today* in Bogotá.
  If the cron skips a day, the missed reminders are gone — they are not rebuilt.
  This is deliberate: a burst of stale notices the morning after an outage is
  noise, not help.
"""

import datetime
import logging
import uuid
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now_utc, today_in_bogota
from app.core.enums import NotificationKind, UserStatus
from app.modules.notifications.schemas import ReminderJobSummary
from app.modules.notifications.service import (
    DeliveryOutcome,
    NotificationContent,
    NotificationsService,
    Recipient,
)
from app.modules.projects.service import ProjectsService
from app.modules.tasks.service import ReminderTask, TasksService
from app.modules.users.service import UsersService

logger = logging.getLogger("kairos.jobs.reminders")

REVIEW_PERMISSION = "task.review"


@dataclass
class _Tally:
    """Running totals for the summary the endpoint answers with."""

    due_soon_sent: int = 0
    overdue_sent: int = 0
    skipped_duplicates: int = 0
    failures: int = 0


async def run_reminders(
    db: AsyncSession, *, today: datetime.date | None = None
) -> ReminderJobSummary:
    """Send the reminders that correspond to today, once each.

    ``today`` is injectable so the tests can place a task three days out without
    waiting three days. In production it is always the calendar day in Bogotá:
    a deadline is a day there, not an instant (RN-26).
    """
    today = today or today_in_bogota()
    tasks_service = TasksService(db)
    projects = ProjectsService(db)
    users = UsersService(db)
    notifications = NotificationsService(db)
    settings = await notifications.get_settings()
    tally = _Tally()

    for days_before in settings.reminder_days_before:
        candidates = await tasks_service.list_reminder_candidates(
            due_on=today + datetime.timedelta(days=days_before)
        )
        await _send_due_soon(
            candidates,
            projects=projects,
            users=users,
            notifications=notifications,
            today=today,
            days_before=days_before,
            tally=tally,
        )

    if settings.overdue_enabled:
        candidates = await tasks_service.list_reminder_candidates(due_before=today)
        await _send_overdue(
            candidates,
            projects=projects,
            users=users,
            notifications=notifications,
            today=today,
            tally=tally,
        )

    logger.info(
        "Recordatorios: %d próximos, %d vencidos, %d omitidos, %d fallidos",
        tally.due_soon_sent,
        tally.overdue_sent,
        tally.skipped_duplicates,
        tally.failures,
    )
    return ReminderJobSummary(
        executed_at=now_utc(),
        due_soon_sent=tally.due_soon_sent,
        overdue_sent=tally.overdue_sent,
        skipped_duplicates=tally.skipped_duplicates,
        failures=tally.failures,
    )


async def _active_projects(
    candidates: list[ReminderTask], projects: ProjectsService
) -> dict[uuid.UUID, str]:
    """Name by id for the projects that are not archived (RN-16, RN-28).

    One query for the whole batch. A task whose project is missing from the
    result is silently dropped, which is exactly what archiving has to do.
    """
    return await projects.active_project_names({t.project_id for t in candidates})


async def _active_recipients(
    user_ids: set[uuid.UUID], users: UsersService
) -> dict[uuid.UUID, Recipient]:
    """The people among these ids who still have an active account (RF-45)."""
    found = await users.get_many(list(user_ids))
    return {
        user.id: Recipient(user_id=user.id, email=user.email, full_name=user.full_name)
        for user in found.values()
        if user.status == UserStatus.ACTIVE
    }


def _count(tally: _Tally, outcome: DeliveryOutcome, *, overdue: bool) -> None:
    if outcome.skipped_duplicate:
        tally.skipped_duplicates += 1
    elif outcome.failed:
        # The in-app notification was still written, so the person is not left
        # uninformed; the dispatch row records the failure (RN-30).
        tally.failures += 1
    elif overdue:
        tally.overdue_sent += 1
    else:
        tally.due_soon_sent += 1


async def _send_due_soon(
    candidates: list[ReminderTask],
    *,
    projects: ProjectsService,
    users: UsersService,
    notifications: NotificationsService,
    today: datetime.date,
    days_before: int,
    tally: _Tally,
) -> None:
    """The advance warning, to the responsibles only (RF-40, RN-25)."""
    if not candidates:
        return
    project_names = await _active_projects(candidates, projects)
    everyone = {
        user_id
        for task in candidates
        if task.project_id in project_names
        for user_id in task.assignee_ids
    }
    recipients = await _active_recipients(everyone, users)

    for task in candidates:
        project_name = project_names.get(task.project_id)
        if project_name is None:
            continue
        content = NotificationContent(
            kind=NotificationKind.TASK_DUE_SOON,
            title=_due_soon_title(days_before),
            body=f"«{task.title}» vence el {task.due_date.isoformat()}.",
            detail=_due_soon_detail(days_before),
            task_id=task.task_id,
            project_id=task.project_id,
            project_name=project_name,
            link_path=f"/proyectos/{task.project_id}/tablero",
        )
        for user_id in sorted(task.assignee_ids):
            recipient = recipients.get(user_id)
            if recipient is None:
                continue
            outcome = await notifications.deliver_reminder(
                recipient, content, target_date=today
            )
            _count(tally, outcome, overdue=False)


async def _send_overdue(
    candidates: list[ReminderTask],
    *,
    projects: ProjectsService,
    users: UsersService,
    notifications: NotificationsService,
    today: datetime.date,
    tally: _Tally,
) -> None:
    """The overdue notice: responsibles **plus** whoever can review (RF-41, RN-25).

    The second group is what makes an unassigned overdue task still visible to
    somebody — the "Tarea vencida sin responsables" scenario of HU-10.
    """
    if not candidates:
        return
    project_names = await _active_projects(candidates, projects)
    live = [task for task in candidates if task.project_id in project_names]
    if not live:
        return

    reviewers: dict[uuid.UUID, set[uuid.UUID]] = {}
    for project_id in {task.project_id for task in live}:
        reviewers[project_id] = await projects.member_ids_with_permission(
            project_id, REVIEW_PERMISSION
        )

    everyone = {
        user_id
        for task in live
        for user_id in task.assignee_ids | reviewers[task.project_id]
    }
    recipients = await _active_recipients(everyone, users)

    for task in live:
        overdue_by = (today - task.due_date).days
        content = NotificationContent(
            kind=NotificationKind.TASK_OVERDUE,
            title="Tarea vencida",
            body=(
                f"«{task.title}» venció el {task.due_date.isoformat()} y sigue sin "
                "terminarse."
            ),
            detail=f"Lleva {overdue_by} día(s) de retraso.",
            task_id=task.task_id,
            project_id=task.project_id,
            project_name=project_names[task.project_id],
            link_path=f"/proyectos/{task.project_id}/tablero",
        )
        # A responsible who can also review is one person and gets one email:
        # the union is a set, and the unique constraint would refuse the second
        # anyway.
        for user_id in sorted(task.assignee_ids | reviewers[task.project_id]):
            recipient = recipients.get(user_id)
            if recipient is None:
                continue
            outcome = await notifications.deliver_reminder(
                recipient, content, target_date=today
            )
            _count(tally, outcome, overdue=True)


def _due_soon_title(days_before: int) -> str:
    if days_before == 0:
        return "Tu tarea vence hoy"
    if days_before == 1:
        return "Tu tarea vence mañana"
    return f"Tu tarea vence en {days_before} días"


def _due_soon_detail(days_before: int) -> str:
    if days_before == 0:
        return "Es el último día para entregarla."
    return "Todavía hay tiempo, pero conviene no dejarlo para el final."
