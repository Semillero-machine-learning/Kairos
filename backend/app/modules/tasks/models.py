"""SQLAlchemy models for the tasks module (tasks, assignees, submissions).

Everything outside this module is referenced by plain foreign key: there is no
relationship() to Project or User, so a board query cannot quietly drag half the
database along (architecture.md 2). Names come from users through
``UsersService.get_many`` at the service layer instead.

Nothing derived is stored. There is no ``assignee_count`` and no ``is_overdue``
column: being overdue is a comparison against today's date in Bogotá, made when
the row is read (data-model.md 8).
"""

import datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, Text, func, text
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import SubmissionReviewStatus, TaskPeriodicity, TaskStatus

__all__ = ["Task", "TaskAssignee", "TaskSubmission"]


task_status_enum = PGEnum(
    TaskStatus,
    name="task_status",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)

task_periodicity_enum = PGEnum(
    TaskPeriodicity,
    name="task_periodicity",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)

submission_review_status_enum = PGEnum(
    SubmissionReviewStatus,
    name="submission_review_status",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("projects.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        task_status_enum, nullable=False, server_default=TaskStatus.BACKLOG.value
    )
    periodicity: Mapped[TaskPeriodicity] = mapped_column(
        task_periodicity_enum,
        nullable=False,
        server_default=TaskPeriodicity.ONE_TIME.value,
    )
    # A calendar day in Colombia, not an instant: a deadline that converted
    # through UTC would fall due at 7 p.m. the previous day.
    due_date: Mapped[datetime.date | None] = mapped_column(Date(), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    completed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Soft delete (RF-37): tasks are never removed physically (RN-17).
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def is_overdue(self, today: datetime.date) -> bool:
        """Past its due date and still unfinished. Computed, never stored."""
        if self.due_date is None or self.status == TaskStatus.DONE:
            return False
        return self.due_date < today


class TaskAssignee(Base):
    """Bridge table. ``assigned_by`` and ``assigned_at`` depend on the whole
    composite key — on the task-user pair, not on either half (data-model.md 8).
    """

    __tablename__ = "task_assignees"

    task_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), primary_key=True
    )
    assigned_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    assigned_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TaskSubmission(Base):
    """A record of work handed in (RF-31). Every one of them is kept: a rejection
    does not erase the previous attempt, it stacks on top of it (RN-09, RF-34).
    """

    __tablename__ = "task_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text(), nullable=False)
    commit_url: Mapped[str | None] = mapped_column(Text(), nullable=True)
    review_status: Mapped[SubmissionReviewStatus] = mapped_column(
        submission_review_status_enum,
        nullable=False,
        server_default=SubmissionReviewStatus.PENDING.value,
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_comment: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
