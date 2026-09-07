"""initial: citext extension and permissions catalog

Revision ID: 0001
Revises:
Create Date: 2026-09-06

Creates the citext extension (case-insensitive email uniqueness) and the
permissions catalog table seeded with the 14 codes from business-rules.md 3.
This table is read-only at runtime; roles are built by choosing from it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (code, category, description) — descriptions shown in the project role editor.
PERMISSIONS: list[tuple[str, str, str]] = [
    ("task.view", "task", "Ver el proyecto, su tablero y sus tareas."),
    ("task.comment", "task", "Comentar en las tareas."),
    ("task.create", "task", "Crear tareas."),
    (
        "task.edit_any",
        "task",
        "Editar título, descripción, periodicidad y fecha límite de cualquier tarea.",
    ),
    ("task.delete", "task", "Eliminar tareas (borrado lógico)."),
    ("task.assign", "task", "Agregar o quitar responsables de una tarea."),
    (
        "task.change_status_any",
        "task",
        "Mover cualquier tarea entre estados, incluidas las ajenas.",
    ),
    ("task.review", "task", "Aprobar o devolver entregas."),
    ("member.add", "member", "Agregar al proyecto usuarios que ya existen en la plataforma."),
    ("member.remove", "member", "Retirar miembros del proyecto."),
    ("role.assign", "role", "Cambiar el rol de proyecto de un miembro."),
    ("role.manage", "role", "Crear, editar y eliminar roles personalizados del proyecto."),
    ("project.edit", "project", "Editar nombre, descripción y fechas del proyecto."),
    ("project.archive", "project", "Archivar y desarchivar el proyecto."),
]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    permissions = op.create_table(
        "permissions",
        sa.Column("code", sa.Text(), primary_key=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
    )

    op.bulk_insert(
        permissions,
        [
            {"code": code, "category": category, "description": description}
            for code, category, description in PERMISSIONS
        ],
    )


def downgrade() -> None:
    op.drop_table("permissions")
    # citext is left in place: other objects may depend on it.
