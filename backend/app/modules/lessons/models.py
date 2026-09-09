"""SQLAlchemy models for the lessons module.

``lessons`` and ``lesson_resources`` do declare relationship() — and that is not
a violation of the rule in CLAUDE.md, which forbids relationships that **cross
modules**. Module, lesson and resource are one aggregate that lives entirely
inside this module, is always read as a whole tree, and is deleted as a whole;
the cascade is the point. The link to ``users`` through ``created_by``, which
does cross a boundary, is a bare foreign key by identifier, like everywhere else.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func, text
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.enums import ResourceType

__all__ = ["Lesson", "LessonModule", "LessonResource"]

resource_type_enum = PGEnum(
    ResourceType,
    name="resource_type",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


class LessonModule(Base):
    """A group of lessons, and the thing that decides visibility (RN-33).

    A published lesson inside a draft module is not visible: the module wins.
    That rule is enforced when the tree is read, not by a constraint, because a
    draft module has to be allowed to contain finished lessons — that is exactly
    how an editor prepares a module before publishing it.
    """

    __tablename__ = "lesson_modules"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    #: Manual order, set by the editor (RF-50). Packed to 0..n-1 on every
    #: reorder, so there are no gaps to reason about.
    position: Mapped[int] = mapped_column(Integer(), nullable=False)
    is_published: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("false")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lessons: Mapped[list["Lesson"]] = relationship(
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.position",
        lazy="selectin",
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("lesson_modules.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)
    is_published: Mapped[bool] = mapped_column(
        Boolean(), nullable=False, server_default=text("false")
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    module: Mapped[LessonModule] = relationship(back_populates="lessons")
    resources: Mapped[list["LessonResource"]] = relationship(
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LessonResource.position",
        lazy="selectin",
    )


class LessonResource(Base):
    """A link, never a file (RN-34).

    ``url`` carries a CHECK for the scheme in the database as well as the
    validation in the schema: the platform hosting nothing is a promise that has
    to hold even for rows written outside the API.
    """

    __tablename__ = "lesson_resources"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    lesson_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[ResourceType] = mapped_column(resource_type_enum, nullable=False)
    title: Mapped[str] = mapped_column(Text(), nullable=False)
    url: Mapped[str] = mapped_column(Text(), nullable=False)
    position: Mapped[int] = mapped_column(Integer(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    lesson: Mapped[Lesson] = relationship(back_populates="resources")
