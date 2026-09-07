"""projects, project_roles, project_role_permissions and project_members

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-07

The project authorization core (RF-13 to RF-24). Two constraints carry most of
the weight:

* ``uq_project_roles_project_lower_name`` enforces RN-20 (role names unique per
  project, case-insensitive) in the database rather than with a Python lookup.
* The composite foreign key on ``project_members`` guarantees that a member's
  role belongs to the same project. data-model.md 4 marks it optional; it is
  included because it is the only way the database itself can reject a role
  borrowed from another project (RN-03, RN-04).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE TYPE project_status AS ENUM ('ACTIVE', 'ARCHIVED')")

    op.create_table(
        "projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="project_status", create_type=False),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.TIMESTAMP(timezone=True), nullable=True),
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
            "char_length(name) BETWEEN 3 AND 120", name="ck_projects_name_length"
        ),
        # Status and timestamp can never drift apart.
        sa.CheckConstraint(
            "(status = 'ARCHIVED') = (archived_at IS NOT NULL)",
            name="ck_projects_archived_consistency",
        ),
    )
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "project_roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("color", sa.Text(), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=True,
        ),
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
            "char_length(name) BETWEEN 2 AND 40", name="ck_project_roles_name_length"
        ),
        sa.CheckConstraint(
            r"color ~ '^#[0-9A-Fa-f]{6}$'", name="ck_project_roles_color_format"
        ),
        # Target of the composite foreign key from project_members.
        sa.UniqueConstraint("id", "project_id", name="uq_project_roles_id_project"),
    )
    # RN-20: unique per project, ignoring case. A functional index, so it cannot
    # be declared as a plain UniqueConstraint.
    op.execute(
        "CREATE UNIQUE INDEX uq_project_roles_project_lower_name "
        "ON project_roles (project_id, lower(name))"
    )

    op.create_table(
        "project_role_permissions",
        sa.Column(
            "project_role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("project_roles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "permission_code",
            sa.Text(),
            sa.ForeignKey("permissions.code", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )

    op.create_table(
        "project_members",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("project_role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "added_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "joined_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # One role per user per project (RN-03).
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        # The role must belong to this very project.
        sa.ForeignKeyConstraint(
            ["project_role_id", "project_id"],
            ["project_roles.id", "project_roles.project_id"],
            name="fk_project_members_role_same_project",
            ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_project_members_user", "project_members", ["user_id"])
    op.create_index("ix_project_members_project", "project_members", ["project_id"])

    for table in ("projects", "project_roles"):
        op.execute(
            f"""
            CREATE TRIGGER {table}_set_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
            """
        )


def downgrade() -> None:
    op.drop_table("project_members")
    op.drop_table("project_role_permissions")
    op.drop_table("project_roles")
    op.drop_table("projects")
    op.execute("DROP TYPE IF EXISTS project_status")
