"""Business rules for tasks, assignees and submissions.

Two things carry this module:

* **The state machine decides who may move what.** ``change_status`` reads the
  transition table of ``state_machine.py`` and never grows a permission check of
  its own (CLAUDE.md). What it does evaluate directly is ownership — being an
  assignee — which is a business rule (RN-10), not an entry in the permission
  catalog.
* **A submission and the move to IN_REVIEW are one transaction.** Handing in work
  that leaves the task in IN_PROGRESS, or a task in review with nothing to
  review, are both states nobody could explain (RF-31).
* **Notifications are sent after the commit, never inside it.** Assignment and
  review both notify (RF-39, RF-42), and RN-30 says a mail failure may not undo
  the operation that caused it. So every ``_notify_*`` helper runs once the
  business change is already durable, and none of them can raise.

This module talks to other modules only through their services, and only in
primitives: it never imports another module's models or repository.
"""

import datetime
import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now_utc, today_in_bogota
from app.core.enums import (
    NotificationKind,
    SubmissionReviewStatus,
    TaskPeriodicity,
    TaskStatus,
    UserStatus,
)
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.core.pagination import Pagination
from app.modules.notifications.service import (
    NotificationContent,
    NotificationsService,
    Recipient,
)
from app.modules.projects.service import ProjectContext, ProjectsService
from app.modules.tasks import state_machine
from app.modules.tasks.models import Task, TaskAssignee, TaskComment, TaskSubmission
from app.modules.tasks.repository import TasksRepository
from app.modules.users.service import UsersService


@dataclass(frozen=True)
class UserSummary:
    """A person's public shape, copied out of the users module at the boundary so
    nothing downstream depends on that module's model."""

    id: uuid.UUID
    full_name: str
    email: str


@dataclass(frozen=True)
class TaskView:
    """A task with everything a response needs, resolved once.

    ``is_overdue`` is computed here, against today's date in Bogotá, and stored
    nowhere (data-model.md 8).
    """

    task: Task
    assignees: list[UserSummary]
    creator: UserSummary
    is_overdue: bool


@dataclass(frozen=True)
class MyTaskView:
    """A row of "Mis tareas": the task plus the project it belongs to (RF-36)."""

    view: TaskView
    project_id: uuid.UUID
    project_name: str


@dataclass(frozen=True)
class SubmissionView:
    submission: TaskSubmission
    submitted_by: UserSummary
    reviewed_by: UserSummary | None


@dataclass(frozen=True)
class ReminderTask:
    """A task the scheduled job might have to remind somebody about.

    Primitives only. ``jobs/reminders.py`` orchestrates three modules and should
    not be holding any of their ORM rows, least of all one whose session it does
    not own.
    """

    task_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    due_date: datetime.date
    assignee_ids: set[uuid.UUID]


@dataclass(frozen=True)
class CommentView:
    comment: TaskComment
    author: UserSummary


@dataclass(frozen=True)
class TaskContext:
    """What a task-scoped request resolved: the task and the project standing of
    whoever asked. Built by ``require_task_permission``, mirroring the way
    ``ProjectContext`` is built by ``require_project_permission``.
    """

    task: Task
    project: ProjectContext

    @property
    def user_id(self) -> uuid.UUID:
        return self.project.user.id

    @property
    def permissions(self) -> frozenset[str]:
        return self.project.permissions


@dataclass(frozen=True)
class SubmissionContext:
    """What a request against ``/submissions/{id}`` resolved.

    Composition rather than three more copies of ``user_id`` and
    ``permissions``: the task context underneath already answers those, and one
    place to change is better than three that can drift.
    """

    submission: TaskSubmission
    task_ctx: TaskContext


@dataclass(frozen=True)
class CommentContext:
    """The same shape for ``/comments/{id}`` (RN-11)."""

    comment: TaskComment
    task_ctx: TaskContext


class TasksService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TasksRepository(db)
        self.projects = ProjectsService(db)
        self.users = UsersService(db)
        self.notifications = NotificationsService(db)

    # --- Reading ---

    async def get_or_404(self, task_id: uuid.UUID) -> Task:
        """A soft-deleted task is gone as far as the API is concerned (RF-37)."""
        task = await self.repo.get_task(task_id)
        if task is None:
            raise NotFoundError("Tarea no encontrada.")
        return task

    async def _summaries(self, user_ids: list[uuid.UUID]) -> dict[uuid.UUID, UserSummary]:
        users = await self.users.get_many(list({user_id for user_id in user_ids}))
        return {
            user_id: UserSummary(
                id=user.id, full_name=user.full_name, email=user.email
            )
            for user_id, user in users.items()
        }

    async def build_views(self, tasks: list[Task]) -> list[TaskView]:
        """Decorate a page of tasks with their assignees and creators in two
        queries, rather than two per card."""
        if not tasks:
            return []
        assignees = await self.repo.assignees_by_task([task.id for task in tasks])
        needed = [task.created_by for task in tasks]
        for ids in assignees.values():
            needed.extend(ids)
        people = await self._summaries(needed)
        today = today_in_bogota()

        views: list[TaskView] = []
        for task in tasks:
            views.append(
                TaskView(
                    task=task,
                    assignees=[
                        people[user_id]
                        for user_id in assignees.get(task.id, [])
                        if user_id in people
                    ],
                    creator=people[task.created_by],
                    is_overdue=task.is_overdue(today),
                )
            )
        return views

    async def build_view(self, task: Task) -> TaskView:
        return (await self.build_views([task]))[0]

    async def list_tasks(
        self,
        ctx: ProjectContext,
        *,
        pagination: Pagination,
        status: TaskStatus | None = None,
        assignee_id: uuid.UUID | None = None,
        periodicity: TaskPeriodicity | None = None,
        overdue: bool = False,
    ) -> tuple[list[TaskView], int]:
        """The board, with the four filters of RF-36."""
        tasks, total = await self.repo.list_tasks(
            project_id=ctx.project_id,
            status=status,
            assignee_id=assignee_id,
            periodicity=periodicity,
            overdue_before=today_in_bogota() if overdue else None,
            offset=pagination.offset,
            limit=pagination.limit,
        )
        return await self.build_views(tasks), total

    async def list_my_tasks(
        self,
        user_id: uuid.UUID,
        *,
        pagination: Pagination,
        status: TaskStatus | None = None,
        due_before: datetime.date | None = None,
    ) -> tuple[list[MyTaskView], int]:
        """Tasks assigned to the user across every project they belong to (RF-36).

        Membership is what makes a project visible, so somebody removed from a
        project stops seeing its tasks here even though the assignment row
        survives, which is what RF-16 and EB-04 ask for.
        """
        names = await self.projects.member_project_names(user_id)
        tasks, total = await self.repo.list_assigned_tasks(
            user_id=user_id,
            project_ids=list(names),
            status=status,
            due_before=due_before,
            offset=pagination.offset,
            limit=pagination.limit,
        )
        views = await self.build_views(tasks)
        return [
            MyTaskView(
                view=view,
                project_id=view.task.project_id,
                project_name=names[view.task.project_id],
            )
            for view in views
        ], total

    async def list_reminder_candidates(
        self,
        *,
        due_on: datetime.date | None = None,
        due_before: datetime.date | None = None,
    ) -> list[ReminderTask]:
        """Unfinished tasks with a deadline on, or before, a given day.

        Only the two conditions this module owns are applied — not DONE, not
        deleted (RN-28) — plus the date. Whether the project is archived and
        whether each responsible is still active belong to the other two modules,
        and the job asks them.
        """
        tasks = await self.repo.list_undone_by_due_date(
            due_on=due_on, due_before=due_before
        )
        if not tasks:
            return []
        assignees = await self.repo.assignees_by_task([task.id for task in tasks])
        return [
            ReminderTask(
                task_id=task.id,
                project_id=task.project_id,
                title=task.title,
                # Non-null by construction: the query demands a deadline.
                due_date=task.due_date,  # type: ignore[arg-type]
                assignee_ids=set(assignees.get(task.id, [])),
            )
            for task in tasks
        ]

    async def count_by_status(self, project_id: uuid.UUID) -> dict[TaskStatus, int]:
        return await self.repo.count_by_status(project_id)

    # --- Writing ---

    async def create_task(
        self,
        ctx: ProjectContext,
        *,
        title: str,
        description: str | None,
        periodicity: TaskPeriodicity,
        due_date: datetime.date | None,
        assignee_ids: list[uuid.UUID],
    ) -> TaskView:
        """Create a task in the project (RF-25).

        It starts in BACKLOG. A due date in the past is accepted on purpose: the
        task may be getting written down late, and the warning belongs to the
        interface (EB-10).
        """
        await self._guard_assignable(ctx.project_id, assignee_ids)

        task = Task(
            project_id=ctx.project_id,
            title=title,
            description=description,
            status=TaskStatus.BACKLOG,
            periodicity=periodicity,
            due_date=due_date,
            created_by=ctx.user.id,
        )
        self.repo.add(task)
        await self.db.flush()

        for user_id in assignee_ids:
            self.repo.add(
                TaskAssignee(
                    task_id=task.id, user_id=user_id, assigned_by=ctx.user.id
                )
            )
        await self.db.commit()

        await self._notify_assigned(task, ctx.project.name, assignee_ids)
        return await self.build_view(task)

    async def update_task(
        self, tctx: TaskContext, *, fields: dict[str, object]
    ) -> TaskView:
        """Edit title, description, periodicity and due date (`task.edit_any`).
        Status is not editable here: it moves through the state machine."""
        for key, value in fields.items():
            setattr(tctx.task, key, value)
        await self.db.commit()
        return await self.build_view(tctx.task)

    async def delete_task(self, tctx: TaskContext) -> None:
        """Soft delete (RF-37). Tasks are never removed physically (RN-17), so the
        submissions and the history they carry survive."""
        tctx.task.deleted_at = now_utc()
        await self.db.commit()

    async def add_assignee(self, tctx: TaskContext, *, user_id: uuid.UUID) -> TaskView:
        """Add someone as responsible for the task (RF-27, `task.assign`)."""
        await self._guard_assignable(tctx.task.project_id, [user_id])
        if user_id in await self.repo.assignee_ids(tctx.task.id):
            raise ConflictError("Esa persona ya es responsable de la tarea.")

        self.repo.add(
            TaskAssignee(
                task_id=tctx.task.id, user_id=user_id, assigned_by=tctx.user_id
            )
        )
        await self.db.commit()

        await self._notify_assigned(
            tctx.task, tctx.project.project.name, [user_id]
        )
        return await self.build_view(tctx.task)

    async def remove_assignee(self, tctx: TaskContext, *, user_id: uuid.UUID) -> TaskView:
        """Drop a responsible. The task survives with one fewer name, and may end
        up with none: the board shows it as unassigned (EB-04)."""
        removed = await self.repo.delete_assignee(tctx.task.id, user_id)
        if removed == 0:
            raise NotFoundError("Esa persona no es responsable de la tarea.")
        await self.db.commit()
        return await self.build_view(tctx.task)

    async def change_status(self, tctx: TaskContext, *, target: TaskStatus) -> TaskView:
        """Move a task between states (RF-28, RF-30).

        The transition table is the authority on every question here: whether the
        move exists, who may make it, and what it demands beforehand.
        """
        task = tctx.task
        transition = state_machine.find(task.status, target)
        if transition is None:
            raise ConflictError(
                self._invalid_transition_message(task.status, target),
                code="INVALID_TRANSITION",
                details=self._transition_details(task.status),
            )
        if transition.via_review_only:
            # Approving has to stamp the submission and sending back has to carry
            # a comment (RN-07, RN-09); a bare status change can do neither.
            raise ConflictError(
                "Una tarea en revisión se resuelve aprobando o devolviendo su "
                "entrega, no cambiando el estado a mano.",
                code="INVALID_TRANSITION",
                details=self._transition_details(task.status),
            )

        is_assignee = tctx.user_id in await self.repo.assignee_ids(task.id)
        if not transition.allows(permissions=tctx.permissions, is_assignee=is_assignee):
            raise ForbiddenError(
                f"Se requiere el permiso «{transition.permission}» para mover una "
                "tarea que no es tuya."
            )

        if (
            transition.requires_submission
            and await self.repo.get_pending_submission(task.id) is None
        ):
            raise ConflictError(
                "Para pasar la tarea a revisión hay que registrar una entrega.",
                code="SUBMISSION_REQUIRED",
            )

        task.status = target
        # RN-08: the two always move together, and the CHECK constraint would
        # reject anything else.
        task.completed_at = now_utc() if target == TaskStatus.DONE else None
        await self.db.commit()
        return await self.build_view(task)

    # --- Submissions ---

    async def list_submissions(self, tctx: TaskContext) -> list[SubmissionView]:
        """The whole history, not just the last one (RF-34)."""
        submissions = await self.repo.list_submissions(tctx.task.id)
        people = await self._summaries(
            [s.submitted_by for s in submissions]
            + [s.reviewed_by for s in submissions if s.reviewed_by is not None]
        )
        return [
            SubmissionView(
                submission=submission,
                submitted_by=people[submission.submitted_by],
                reviewed_by=(
                    people.get(submission.reviewed_by)
                    if submission.reviewed_by
                    else None
                ),
            )
            for submission in submissions
        ]

    async def create_submission(
        self, tctx: TaskContext, *, description: str, commit_url: str | None
    ) -> tuple[SubmissionView, TaskView]:
        """Hand in the work and move the task to IN_REVIEW, in one transaction
        (RF-31)."""
        task = tctx.task
        if tctx.user_id not in await self.repo.assignee_ids(task.id):
            raise ForbiddenError(
                "Solo un responsable de la tarea puede registrar la entrega.",
                code="NOT_ASSIGNEE",
            )

        # Checked here so the error says which of the two things went wrong; the
        # partial unique index below is what actually guarantees it.
        if await self.repo.get_pending_submission(task.id) is not None:
            raise ConflictError(
                "Esta tarea ya tiene una entrega sin revisar.",
                code="SUBMISSION_ALREADY_PENDING",
            )

        transition = state_machine.find(task.status, TaskStatus.IN_REVIEW)
        if transition is None:
            raise ConflictError(
                self._invalid_transition_message(task.status, TaskStatus.IN_REVIEW),
                code="INVALID_TRANSITION",
                details=self._transition_details(task.status),
            )

        submission = TaskSubmission(
            task_id=task.id,
            submitted_by=tctx.user_id,
            description=description,
            commit_url=commit_url,
        )
        self.repo.add(submission)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            # Two submissions racing: the partial unique index decides, not a
            # check made moments earlier.
            raise ConflictError(
                "Esta tarea ya tiene una entrega sin revisar.",
                code="SUBMISSION_ALREADY_PENDING",
            ) from exc

        task.status = TaskStatus.IN_REVIEW
        await self.db.commit()

        author = (await self._summaries([tctx.user_id]))[tctx.user_id]
        return (
            SubmissionView(submission=submission, submitted_by=author, reviewed_by=None),
            await self.build_view(task),
        )

    async def get_submission_or_404(self, submission_id: uuid.UUID) -> TaskSubmission:
        submission = await self.repo.get_submission(submission_id)
        if submission is None:
            raise NotFoundError("Entrega no encontrada.")
        return submission

    async def update_submission(
        self, sctx: SubmissionContext, *, fields: dict[str, object]
    ) -> SubmissionView:
        """Correct your own submission while nobody has looked at it (RN-12).

        Being the author is what authorizes this, not a permission of the
        catalog: the guard only established that the person can see the task.
        """
        submission = sctx.submission
        if sctx.task_ctx.user_id != submission.submitted_by:
            raise ForbiddenError("Solo quien registró la entrega puede editarla.")
        # The two conditions of RN-12. They coincide today — a pending submission
        # only stops being pending through the review endpoint, which is also
        # what moves the task out of IN_REVIEW — but the rule states both and a
        # future path that separates them should fail here, not silently pass.
        if (
            submission.review_status != SubmissionReviewStatus.PENDING
            or sctx.task_ctx.task.status != TaskStatus.IN_REVIEW
        ):
            raise ConflictError(
                "La entrega ya fue revisada y no se puede editar.",
                code="SUBMISSION_ALREADY_REVIEWED",
            )

        for key, value in fields.items():
            setattr(submission, key, value)
        await self.db.commit()

        author = (await self._summaries([submission.submitted_by]))[
            submission.submitted_by
        ]
        return SubmissionView(
            submission=submission, submitted_by=author, reviewed_by=None
        )

    async def review_submission(
        self, sctx: SubmissionContext, *, approved: bool, comment: str | None
    ) -> tuple[SubmissionView, TaskView]:
        """Approve or send back a submission (RF-33).

        Two rules that no other path enforces:

        * **RN-07, the second pair of eyes.** A reviewer who is also responsible
          for the task is refused, even holding ``task.review``. The rule spells
          out approval; sending back is refused just the same, because it is the
          other way out of IN_REVIEW and letting a responsible take it would give
          back with one hand what the rule took with the other.
        * **RN-09, a rejection explains itself.** Refused here rather than by a
          schema validator, so the answer carries REVIEW_COMMENT_REQUIRED and the
          interface can point at the right field (api-contract.md 6).
        """
        submission = sctx.submission
        task = sctx.task_ctx.task
        reviewer_id = sctx.task_ctx.user_id

        if reviewer_id in await self.repo.assignee_ids(task.id):
            raise ForbiddenError(
                "No puedes revisar una entrega de una tarea de la que eres "
                "responsable. La revisión la hace otra persona.",
                code="CANNOT_REVIEW_OWN_SUBMISSION",
            )
        if submission.review_status != SubmissionReviewStatus.PENDING:
            raise ConflictError(
                "Esta entrega ya fue revisada.", code="SUBMISSION_ALREADY_REVIEWED"
            )
        if not approved and not comment:
            raise ValidationError(
                "Para devolver una entrega hay que explicar qué falta.",
                code="REVIEW_COMMENT_REQUIRED",
            )

        target = TaskStatus.DONE if approved else TaskStatus.IN_PROGRESS
        transition = state_machine.find(task.status, target)
        if transition is None:
            raise ConflictError(
                self._invalid_transition_message(task.status, target),
                code="INVALID_TRANSITION",
                details=self._transition_details(task.status),
            )

        submission.review_status = (
            SubmissionReviewStatus.APPROVED if approved else SubmissionReviewStatus.REJECTED
        )
        submission.reviewed_by = reviewer_id
        submission.reviewed_at = now_utc()
        # Kept on an approval too: praise is history as much as a correction is.
        submission.review_comment = comment
        task.status = target
        # RN-08: completed_at and the state move together, always.
        task.completed_at = now_utc() if approved else None
        await self.db.commit()

        people = await self._summaries([submission.submitted_by, reviewer_id])
        await self._notify_reviewed(
            task,
            sctx.task_ctx.project.project.name,
            author=people[submission.submitted_by],
            reviewer=people[reviewer_id],
            approved=approved,
            comment=comment,
        )
        return (
            SubmissionView(
                submission=submission,
                submitted_by=people[submission.submitted_by],
                reviewed_by=people[reviewer_id],
            ),
            await self.build_view(task),
        )

    # --- Comments ---

    async def list_comments(self, tctx: TaskContext) -> list[CommentView]:
        """The thread of a task (RF-35), oldest first."""
        comments = await self.repo.list_comments(tctx.task.id)
        people = await self._summaries([c.author_id for c in comments])
        return [
            CommentView(comment=comment, author=people[comment.author_id])
            for comment in comments
        ]

    async def create_comment(self, tctx: TaskContext, *, body: str) -> CommentView:
        """Add a message to the thread (`task.comment`)."""
        comment = TaskComment(task_id=tctx.task.id, author_id=tctx.user_id, body=body)
        self.repo.add(comment)
        await self.db.commit()
        author = (await self._summaries([tctx.user_id]))[tctx.user_id]
        return CommentView(comment=comment, author=author)

    async def get_comment_or_404(self, comment_id: uuid.UUID) -> TaskComment:
        comment = await self.repo.get_comment(comment_id)
        if comment is None:
            raise NotFoundError("Comentario no encontrado.")
        return comment

    async def update_comment(self, cctx: CommentContext, *, body: str) -> CommentView:
        """Only the author edits a comment (RN-11). Moderation can delete, never
        rewrite: putting words in someone's mouth is worse than removing them."""
        if cctx.task_ctx.user_id != cctx.comment.author_id:
            raise ForbiddenError("Solo el autor puede editar su comentario.")
        cctx.comment.body = body
        await self.db.commit()
        author = (await self._summaries([cctx.comment.author_id]))[
            cctx.comment.author_id
        ]
        return CommentView(comment=cctx.comment, author=author)

    async def delete_comment(self, cctx: CommentContext) -> None:
        """The author, or a moderator holding ``task.delete`` (RN-11).

        Soft delete, like everything else here (RN-17): the message leaves the
        conversation, the row stays.
        """
        is_author = cctx.task_ctx.user_id == cctx.comment.author_id
        if not is_author and "task.delete" not in cctx.task_ctx.permissions:
            raise ForbiddenError(
                "Solo el autor, o alguien con «task.delete» para moderar, puede "
                "borrar este comentario."
            )
        cctx.comment.deleted_at = now_utc()
        await self.db.commit()

    # --- Notifications (RF-39, RF-42) ---

    @staticmethod
    def _board_path(project_id: uuid.UUID) -> str:
        """Where the email's button lands.

        The board of the project, not the task: the frontend has no route that
        opens one card directly, and a link that half works is worse than one
        that lands next to what it promised.
        """
        return f"/proyectos/{project_id}/tablero"

    @staticmethod
    def _deadline_line(due_date: datetime.date | None) -> str:
        if due_date is None:
            return "La tarea no tiene fecha límite."
        return f"Fecha límite: {due_date.isoformat()}."

    async def _notify_assigned(
        self, task: Task, project_name: str, user_ids: list[uuid.UUID]
    ) -> None:
        """Tell the new responsibles (RF-39).

        Called after the commit, and never able to break it: the delivery service
        swallows every mail failure (RN-30). The people are looked up here rather
        than passed in because ``_guard_assignable`` has already established they
        exist and are active.
        """
        if not user_ids:
            return
        people = await self._summaries(user_ids)
        content = NotificationContent(
            kind=NotificationKind.TASK_ASSIGNED,
            title="Te asignaron una tarea",
            body=f"Ahora eres responsable de «{task.title}».",
            detail=self._deadline_line(task.due_date),
            task_id=task.id,
            project_id=task.project_id,
            project_name=project_name,
            link_path=self._board_path(task.project_id),
        )
        for user_id in user_ids:
            person = people.get(user_id)
            if person is None:
                continue
            await self.notifications.deliver(
                Recipient(
                    user_id=person.id, email=person.email, full_name=person.full_name
                ),
                content,
            )

    async def _notify_reviewed(
        self,
        task: Task,
        project_name: str,
        *,
        author: UserSummary,
        reviewer: UserSummary,
        approved: bool,
        comment: str | None,
    ) -> None:
        """Tell whoever handed the work in how it went (RF-42, RN-25).

        Only the author: the reviewer already knows, and everybody else finds out
        from the board.
        """
        if approved:
            kind = NotificationKind.SUBMISSION_APPROVED
            title = "Aprobaron tu entrega"
            body = (
                f"{reviewer.full_name} aprobó tu entrega de «{task.title}». "
                "La tarea quedó terminada."
            )
        else:
            kind = NotificationKind.SUBMISSION_REJECTED
            title = "Devolvieron tu entrega"
            body = (
                f"{reviewer.full_name} devolvió tu entrega de «{task.title}». "
                "La tarea volvió a «en progreso»."
            )
        await self.notifications.deliver(
            Recipient(
                user_id=author.id, email=author.email, full_name=author.full_name
            ),
            NotificationContent(
                kind=kind,
                title=title,
                body=body,
                detail=comment,
                task_id=task.id,
                project_id=task.project_id,
                project_name=project_name,
                link_path=self._board_path(task.project_id),
            ),
        )

    # --- Guards ---

    async def _guard_assignable(
        self, project_id: uuid.UUID, user_ids: list[uuid.UUID]
    ) -> None:
        """A responsible has to be an active member of the project.

        Someone outside the project cannot even see the task they would be
        responsible for, and a deactivated user neither works nor gets notified
        (RF-09). Losing membership later does not undo the assignment: the task
        keeps its history and simply shows one fewer name (RF-16, EB-04).
        """
        if not user_ids:
            return

        members = await self.projects.member_user_ids(project_id)
        outsiders = [user_id for user_id in user_ids if user_id not in members]
        if outsiders:
            raise ValidationError(
                "Solo se pueden asignar tareas a miembros del proyecto.",
                details={"not_members": [str(user_id) for user_id in outsiders]},
            )

        users = await self.users.get_many(user_ids)
        missing = [user_id for user_id in user_ids if user_id not in users]
        if missing:
            raise NotFoundError("Alguno de los responsables no existe.")
        inactive = [
            str(user_id)
            for user_id, user in users.items()
            if user.status != UserStatus.ACTIVE
        ]
        if inactive:
            raise ValidationError(
                "Solo se pueden asignar tareas a usuarios activos.",
                details={"inactive": inactive},
            )

    @staticmethod
    def _invalid_transition_message(source: TaskStatus, target: TaskStatus) -> str:
        allowed = state_machine.allowed_targets(source)
        if not allowed:
            return f"Una tarea en «{source}» no se puede mover a ningún otro estado."
        return (
            f"No se puede pasar de «{source}» a «{target}». "
            f"Desde «{source}» solo se puede ir a: {', '.join(allowed)}."
        )

    @staticmethod
    def _transition_details(source: TaskStatus) -> dict[str, object]:
        return {
            "from": source.value,
            "allowed": [status.value for status in state_machine.allowed_targets(source)],
        }
