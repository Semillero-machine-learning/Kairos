"""notification_settings singleton row

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-06

Global reminder configuration (RF-43, RN-26). A single row pinned to id = 1,
seeded with the documented defaults: days [3, 1, 0], send hour 07:00
America/Bogota, overdue notices enabled.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notification_settings",
        sa.Column("id", sa.SmallInteger(), primary_key=True, autoincrement=False),
        sa.Column(
            "reminder_days_before",
            postgresql.ARRAY(sa.Integer()),
            nullable=False,
            server_default=sa.text("'{3,1,0}'"),
        ),
        sa.Column("send_hour", sa.SmallInteger(), nullable=False, server_default=sa.text("7")),
        sa.Column(
            "timezone", sa.Text(), nullable=False, server_default=sa.text("'America/Bogota'")
        ),
        sa.Column(
            "overdue_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("id = 1", name="ck_notification_settings_singleton"),
        sa.CheckConstraint(
            "send_hour BETWEEN 0 AND 23", name="ck_notification_settings_send_hour"
        ),
    )

    # Seed the single configuration row with the documented defaults.
    op.execute("INSERT INTO notification_settings (id) VALUES (1)")


def downgrade() -> None:
    op.drop_table("notification_settings")
