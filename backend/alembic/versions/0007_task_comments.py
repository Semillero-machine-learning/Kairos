"""task_comments

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-08

The comment thread of a task (RF-35). The submissions table already arrived with
0006 carrying every review constraint, so the review half of this phase needs no
schema change: approving and returning only write columns that already exist.

Comments are soft-deleted like tasks are (RN-17): a moderated comment leaves the
thread but the row stays, and the partial index is what keeps the common read —
the live thread of one task — off the deleted rows.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_comments",
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
            "author_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
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
            "char_length(body) BETWEEN 1 AND 4000",
            name="ck_task_comments_body_length",
        ),
    )
    # The live thread of a task, oldest first: a conversation is read downwards.
    op.create_index(
        "ix_task_comments_task",
        "task_comments",
        ["task_id", "created_at"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.execute(
        """
        CREATE TRIGGER task_comments_set_updated_at
        BEFORE UPDATE ON task_comments
        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
        """
    )


def downgrade() -> None:
    op.drop_table("task_comments")
