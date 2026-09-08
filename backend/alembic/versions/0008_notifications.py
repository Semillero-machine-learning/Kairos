"""notifications and notification_dispatches

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-08

The two tables the notification system runs on (RF-38 to RF-45).

``uq_notification_dispatches_once`` is the whole point of this migration. RN-27
says a user never gets the same reminder for the same task twice in one day, and
that promise is kept by this unique constraint and by nothing else: the job
inserts here **before** it sends, and a conflict is what tells it the email
already went out. A check made in Python beforehand would leave a race window
between the read and the write; a unique index has none, even across two
concurrent runs of the job.

``NULLS NOT DISTINCT`` is not decoration. ``task_id`` is nullable, and under the
default semantics two NULLs never collide, so any future notification kind that
is not tied to a task would slip past the constraint and be sent again on every
run. Every reminder carries a task today; the constraint is written so it still
holds the day one does not.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE notification_kind AS ENUM "
        "('TASK_ASSIGNED', 'TASK_DUE_SOON', 'TASK_OVERDUE', "
        "'SUBMISSION_APPROVED', 'SUBMISSION_REJECTED')"
    )
    op.execute("CREATE TYPE dispatch_status AS ENUM ('SENT', 'FAILED')")

    op.create_table(
        "notifications",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kind",
            postgresql.ENUM(name="notification_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("read_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # The bell's history: one user's notifications, newest first.
    op.create_index(
        "ix_notifications_user_created",
        "notifications",
        ["user_id", sa.text("created_at DESC")],
    )
    # The unread counter, polled every 60 seconds by every open tab: it has to
    # be cheap, and a partial index keeps it off the read rows entirely.
    op.create_index(
        "ix_notifications_unread",
        "notifications",
        ["user_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )

    op.create_table(
        "notification_dispatches",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "kind",
            postgresql.ENUM(name="notification_kind", create_type=False),
            nullable=False,
        ),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="dispatch_status", create_type=False),
            nullable=False,
        ),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "attempts", sa.SmallInteger(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # RN-27, enforced by the database. See the module docstring.
    op.execute(
        """
        ALTER TABLE notification_dispatches
        ADD CONSTRAINT uq_notification_dispatches_once
        UNIQUE NULLS NOT DISTINCT (user_id, task_id, kind, target_date)
        """
    )


def downgrade() -> None:
    op.drop_table("notification_dispatches")
    op.drop_table("notifications")
    op.execute("DROP TYPE IF EXISTS dispatch_status")
    op.execute("DROP TYPE IF EXISTS notification_kind")
