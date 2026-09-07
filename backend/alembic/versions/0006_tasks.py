"""tasks, task_assignees and task_submissions

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-07

The task lifecycle (RF-25 to RF-32, RF-37). Three constraints do work that the
application deliberately does not repeat:

* ``ck_tasks_done_completed_at`` keeps ``status = 'DONE'`` and ``completed_at``
  from ever drifting apart (RN-08).
* ``uq_task_submissions_pending`` is a partial unique index: one pending
  submission per task, enforced by the database instead of by a read-then-write
  in Python, which always leaves a race window (RF-31).
* ``ck_task_submissions_rejected_comment`` refuses a rejection with no
  explanation, which is what RN-09 and RF-33 ask for.

No column stores anything derived: whether a task is overdue is a comparison
against today's date in Bogotá, computed on read (data-model.md 8).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE task_status AS ENUM "
        "('BACKLOG', 'TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE')"
    )
    op.execute(
        "CREATE TYPE task_periodicity AS ENUM "
        "('ONE_TIME', 'WEEKLY', 'MONTHLY', 'SEMESTER')"
    )
    op.execute(
        "CREATE TYPE submission_review_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED')"
    )

    op.create_table(
        "tasks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="task_status", create_type=False),
            nullable=False,
            server_default="BACKLOG",
        ),
        sa.Column(
            "periodicity",
            postgresql.ENUM(name="task_periodicity", create_type=False),
            nullable=False,
            server_default="ONE_TIME",
        ),
        # A date, not a timestamp: the deadline is a calendar day in Colombia.
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "char_length(title) BETWEEN 3 AND 200", name="ck_tasks_title_length"
        ),
        sa.CheckConstraint(
            "(status = 'DONE') = (completed_at IS NOT NULL)",
            name="ck_tasks_done_completed_at",
        ),
    )
    # The board query.
    op.create_index(
        "ix_tasks_project_status",
        "tasks",
        ["project_id", "status"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    # The scheduler query (Phase 5), and the "overdue" filter of the board.
    op.create_index(
        "ix_tasks_due_date",
        "tasks",
        ["due_date"],
        postgresql_where=sa.text("deleted_at IS NULL AND status <> 'DONE'"),
    )

    op.create_table(
        "task_assignees",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "assigned_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "assigned_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # "Mis tareas" across every project (RF-36).
    op.create_index("ix_task_assignees_user", "task_assignees", ["user_id"])

    op.create_table(
        "task_submissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "submitted_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("commit_url", sa.Text(), nullable=True),
        sa.Column(
            "review_status",
            postgresql.ENUM(name="submission_review_status", create_type=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column(
            "reviewed_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "char_length(description) BETWEEN 10 AND 4000",
            name="ck_task_submissions_description_length",
        ),
        # The platform hosts no files: a submission points at GitHub (RF-32, RN-34).
        sa.CheckConstraint(
            r"commit_url IS NULL OR commit_url ~ '^https://github\.com/'",
            name="ck_task_submissions_commit_url",
        ),
        sa.CheckConstraint(
            "(review_status = 'PENDING') = (reviewed_at IS NULL)",
            name="ck_task_submissions_reviewed_at",
        ),
        # Sending a submission back demands an explanation (RN-09).
        sa.CheckConstraint(
            "review_status <> 'REJECTED' OR review_comment IS NOT NULL",
            name="ck_task_submissions_rejected_comment",
        ),
    )
    # One pending submission per task, decided by the database (RF-31).
    op.create_index(
        "uq_task_submissions_pending",
        "task_submissions",
        ["task_id"],
        unique=True,
        postgresql_where=sa.text("review_status = 'PENDING'"),
    )
    # The submission history of a task, newest first (RF-34).
    op.create_index("ix_task_submissions_task", "task_submissions", ["task_id", "created_at"])

    op.execute(
        """
        CREATE TRIGGER tasks_set_updated_at
        BEFORE UPDATE ON tasks
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.drop_table("task_submissions")
    op.drop_table("task_assignees")
    op.drop_table("tasks")
    op.execute("DROP TYPE IF EXISTS submission_review_status")
    op.execute("DROP TYPE IF EXISTS task_periodicity")
    op.execute("DROP TYPE IF EXISTS task_status")
