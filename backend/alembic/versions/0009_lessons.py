"""lesson_modules, lessons and lesson_resources

Revision ID: 0009
Revises: 0008
Create Date: 2026-09-09

El catálogo de lecciones (RF-46 a RF-52), tal como lo describe data-model.md 7.

Dos decisiones que la tabla no explica por sí sola:

``ON DELETE CASCADE`` en las dos llaves foráneas es RN-36 escrito en el esquema:
al borrar un módulo se van sus lecciones, y con ellas sus recursos. La interfaz
avisa antes con el conteo exacto, pero el borrado en cadena lo hace la base, no
un bucle en Python que puede quedarse a medias.

``ck_lesson_resources_url_scheme`` repite en la base lo que el esquema Pydantic
ya valida. No es redundancia inútil: es RN-34 —la plataforma no aloja archivos,
todo recurso es una URL externa— y esa promesa tiene que sobrevivir a una carga
de datos hecha por fuera de la API.

Ninguna de las tres tablas guarda dato derivado alguno: el conteo de recursos
que devuelve el árbol se calcula al consultar (data-model.md 8).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE resource_type AS ENUM "
        "('NOTEBOOK', 'PDF', 'VIDEO', 'REPOSITORY', 'ARTICLE')"
    )

    op.create_table(
        "lesson_modules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            # RESTRICT y no CASCADE: un módulo publicado no desaparece porque se
            # borre la cuenta de quien lo creó. Las cuentas se desactivan, no se
            # borran (RN-44), así que en la práctica no se llega aquí.
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
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
            "char_length(title) BETWEEN 3 AND 150", name="ck_lesson_modules_title_length"
        ),
    )
    # El catálogo se lee entero y ordenado, siempre.
    op.create_index("ix_lesson_modules_position", "lesson_modules", ["position"])

    op.create_table(
        "lessons",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "module_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lesson_modules.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "is_published",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
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
            "char_length(title) BETWEEN 3 AND 150", name="ck_lessons_title_length"
        ),
    )
    op.create_index("ix_lessons_module_position", "lessons", ["module_id", "position"])

    op.create_table(
        "lesson_resources",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "lesson_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "type",
            postgresql.ENUM(name="resource_type", create_type=False),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "char_length(title) BETWEEN 1 AND 200", name="ck_lesson_resources_title_length"
        ),
        sa.CheckConstraint("url ~ '^https?://'", name="ck_lesson_resources_url_scheme"),
    )
    op.create_index(
        "ix_lesson_resources_lesson_position", "lesson_resources", ["lesson_id", "position"]
    )


def downgrade() -> None:
    op.drop_table("lesson_resources")
    op.drop_table("lessons")
    op.drop_table("lesson_modules")
    op.execute("DROP TYPE resource_type")
