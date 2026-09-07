"""Data access for tasks, assignees and submissions. Queries only, no decisions.

Every read filters out soft-deleted tasks: a deleted task is gone as far as the
rest of the system is concerned, and leaving that filter to the callers would
mean remembering it in eight places (RF-37).
"""

import datetime
import uuid

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubmissionReviewStatus, TaskPeriodicity, TaskStatus
from app.modules.tasks.models import Task, TaskAssignee, TaskSubmission


class TasksRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, obj: object) -> None:
        self.db.add(obj)

    # --- Tasks ---

    async def get_task(self, task_id: uuid.UUID) -> Task | None:
        result = await self.db.execute(
            select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    def _filtered(
        self,
        query: Select,
        *,
        status: TaskStatus | None,
        assignee_id: uuid.UUID | None,
        periodicity: TaskPeriodicity | None,
        overdue_before: datetime.date | None,
    ) -> Select:
        """The four board filters of RF-36, applied to any base query."""
        if status is not None:
            query = query.where(Task.status == status)
        if periodicity is not None:
            query = query.where(Task.periodicity == periodicity)
        if assignee_id is not None:
            query = query.where(
                select(TaskAssignee.task_id)
                .where(
                    TaskAssignee.task_id == Task.id,
                    TaskAssignee.user_id == assignee_id,
                )
                .exists()
            )
        if overdue_before is not None:
            # Overdue is a comparison, never a stored column (data-model.md 8).
            query = query.where(
                Task.due_date.is_not(None),
                Task.due_date < overdue_before,
                Task.status != TaskStatus.DONE,
            )
        return query

    @staticmethod
    def _ordered(query: Select) -> Select:
        """Soonest deadline first; undated tasks last, oldest first among equals."""
        return query.order_by(Task.due_date.asc().nulls_last(), Task.created_at.asc())

    async def list_tasks(
        self,
        *,
        project_id: uuid.UUID,
        status: TaskStatus | None = None,
        assignee_id: uuid.UUID | None = None,
        periodicity: TaskPeriodicity | None = None,
        overdue_before: datetime.date | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        base = select(Task).where(Task.project_id == project_id, Task.deleted_at.is_(None))
        base = self._filtered(
            base,
            status=status,
            assignee_id=assignee_id,
            periodicity=periodicity,
            overdue_before=overdue_before,
        )
        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = await self.db.execute(self._ordered(base).offset(offset).limit(limit))
        return list(rows.scalars().all()), total

    async def list_assigned_tasks(
        self,
        *,
        user_id: uuid.UUID,
        project_ids: list[uuid.UUID],
        status: TaskStatus | None = None,
        due_before: datetime.date | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Task], int]:
        """The user's own tasks across projects (RF-36).

        ``project_ids`` is resolved by the projects service, so this module never
        queries another module's tables to find out where the user belongs.
        """
        if not project_ids:
            return [], 0

        base = (
            select(Task)
            .join(TaskAssignee, TaskAssignee.task_id == Task.id)
            .where(
                TaskAssignee.user_id == user_id,
                Task.project_id.in_(project_ids),
                Task.deleted_at.is_(None),
            )
        )
        if status is not None:
            base = base.where(Task.status == status)
        if due_before is not None:
            base = base.where(Task.due_date.is_not(None), Task.due_date <= due_before)

        total = (
            await self.db.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = await self.db.execute(self._ordered(base).offset(offset).limit(limit))
        return list(rows.scalars().all()), total

    async def count_by_status(self, project_id: uuid.UUID) -> dict[TaskStatus, int]:
        """Board tallies for one project. Derived on every read: there is no
        counter column anywhere (data-model.md 8)."""
        rows = await self.db.execute(
            select(Task.status, func.count())
            .where(Task.project_id == project_id, Task.deleted_at.is_(None))
            .group_by(Task.status)
        )
        return {status: count for status, count in rows.all()}

    # --- Assignees ---

    async def assignee_ids(self, task_id: uuid.UUID) -> set[uuid.UUID]:
        rows = await self.db.execute(
            select(TaskAssignee.user_id).where(TaskAssignee.task_id == task_id)
        )
        return set(rows.scalars().all())

    async def assignees_by_task(
        self, task_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, list[uuid.UUID]]:
        """Assignees for a page of tasks in one query, so a board of forty cards
        does not become forty round trips."""
        if not task_ids:
            return {}
        rows = await self.db.execute(
            select(TaskAssignee.task_id, TaskAssignee.user_id)
            .where(TaskAssignee.task_id.in_(task_ids))
            .order_by(TaskAssignee.assigned_at)
        )
        grouped: dict[uuid.UUID, list[uuid.UUID]] = {task_id: [] for task_id in task_ids}
        for task_id, user_id in rows.all():
            grouped[task_id].append(user_id)
        return grouped

    async def delete_assignee(self, task_id: uuid.UUID, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            delete(TaskAssignee).where(
                TaskAssignee.task_id == task_id, TaskAssignee.user_id == user_id
            )
        )
        return result.rowcount or 0

    # --- Submissions ---

    async def get_submission(self, submission_id: uuid.UUID) -> TaskSubmission | None:
        return await self.db.get(TaskSubmission, submission_id)

    async def get_pending_submission(self, task_id: uuid.UUID) -> TaskSubmission | None:
        result = await self.db.execute(
            select(TaskSubmission).where(
                TaskSubmission.task_id == task_id,
                TaskSubmission.review_status == SubmissionReviewStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def list_submissions(self, task_id: uuid.UUID) -> list[TaskSubmission]:
        """The full history, newest first. Nothing is ever removed (RN-09, RF-34)."""
        rows = await self.db.execute(
            select(TaskSubmission)
            .where(TaskSubmission.task_id == task_id)
            .order_by(TaskSubmission.created_at.desc())
        )
        return list(rows.scalars().all())
