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

This module talks to other modules only through their services, and only in
primitives: it never imports another module's models or repository.
"""

import datetime
import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import now_utc, today_in_bogota
from app.core.enums import TaskPeriodicity, TaskStatus, UserStatus
from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ValidationError,
)
from app.core.pagination import Pagination
from app.modules.projects.service import ProjectContext, ProjectsService
from app.modules.tasks import state_machine
from app.modules.tasks.models import Task, TaskAssignee, TaskSubmission
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


class TasksService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = TasksRepository(db)
        self.projects = ProjectsService(db)
        self.users = UsersService(db)

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
