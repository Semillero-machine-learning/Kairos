"""Business rules for the lesson catalog (RN-31 a RN-36).

Like notifications, this service **imports nothing from any other module**
(architecture.md 2: ``lessons → ninguno``). It never receives a ``User``: the
router resolves who is asking into two primitives — ``can_edit`` and, when
something is created, the author's identifier — and hands those down. That is
what keeps the catalog independent of projects, tasks and everything else, which
is the whole reason the roadmap allows building it in parallel.

Two rules carry most of the weight here:

* **RN-32 and RN-33 (visibility).** Drafts belong to editors only, and a
  published lesson inside a draft module is invisible because the module wins.
  Both are applied in one place, ``_visible_lessons`` and the filter above it,
  so there is no second path that could forget one of them.
* **RN-36 (deletion).** Removing a module takes its lessons and their resources
  with it, and the caller has to say so explicitly.

Transactions are opened and committed here, never in the repository or the
router.
"""

import uuid
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import GlobalRole, ResourceType
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.lessons.models import Lesson, LessonModule, LessonResource
from app.modules.lessons.repository import LessonsRepository

#: Who may write the catalog (RN-31). A project leader is not here on purpose:
#: leading a project says nothing about the study material.
EDITOR_ROLES: frozenset[GlobalRole] = frozenset(
    {GlobalRole.ADMIN, GlobalRole.LESSON_EDITOR}
)


def can_edit_lessons(role: GlobalRole) -> bool:
    return role in EDITOR_ROLES


class Orderable(Protocol):
    """What the three levels of the catalog have in common for ordering."""

    id: uuid.UUID
    position: int


@dataclass(frozen=True)
class CatalogModule:
    """A module paired with the lessons this particular viewer may see.

    Kept apart from the ORM object instead of trimming ``module.lessons`` in
    place: mutating a loaded collection to express a permission decision would
    write that decision back to the database on the next flush.
    """

    module: LessonModule
    lessons: list[Lesson]


class LessonsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = LessonsRepository(db)

    # --- Reading the catalog ---

    async def list_catalog(
        self, *, can_edit: bool, query: str | None = None
    ) -> list[CatalogModule]:
        """The whole tree, as this viewer is allowed to see it (RF-51).

        Visibility first, search second, and that order matters: filtering by
        text before hiding the drafts would let a search reveal that a draft
        exists by the shape of what comes back.
        """
        modules = await self.repo.list_modules()
        catalog = [
            CatalogModule(module=module, lessons=self._visible_lessons(module, can_edit))
            for module in modules
            if can_edit or module.is_published
        ]
        return self._search(catalog, query)

    @staticmethod
    def _visible_lessons(module: LessonModule, can_edit: bool) -> list[Lesson]:
        if can_edit:
            return list(module.lessons)
        return [lesson for lesson in module.lessons if lesson.is_published]

    @staticmethod
    def _matches(text: str | None, needle: str) -> bool:
        return text is not None and needle in text.casefold()

    @classmethod
    def _search(cls, catalog: list[CatalogModule], query: str | None) -> list[CatalogModule]:
        """Filter by title or description, over modules and lessons alike (RF-51).

        A module that matches keeps all of its visible lessons: the person
        searched for the module and wants to see what is in it. A module that
        does not match survives only through its matching lessons, and shows just
        those, because that is what the search was about.
        """
        needle = (query or "").strip().casefold()
        if not needle:
            return catalog

        results: list[CatalogModule] = []
        for entry in catalog:
            if cls._matches(entry.module.title, needle) or cls._matches(
                entry.module.description, needle
            ):
                results.append(entry)
                continue
            hits = [
                lesson
                for lesson in entry.lessons
                if cls._matches(lesson.title, needle)
                or cls._matches(lesson.description, needle)
            ]
            if hits:
                results.append(CatalogModule(module=entry.module, lessons=hits))
        return results

    # --- Modules ---

    async def get_module_or_404(self, module_id: uuid.UUID) -> LessonModule:
        module = await self.repo.get_module(module_id)
        if module is None:
            raise NotFoundError("Módulo no encontrado.")
        return module

    async def create_module(
        self, *, title: str, description: str | None, created_by: uuid.UUID
    ) -> LessonModule:
        """A module is born as a draft (RF-49): nothing reaches the semillero
        until an editor decides it is ready."""
        module = LessonModule(
            title=title,
            description=description,
            position=await self.repo.next_module_position(),
            is_published=False,
            created_by=created_by,
        )
        self.repo.add(module)
        await self.db.commit()
        await self.db.refresh(module)
        return module

    async def update_module(
        self, module_id: uuid.UUID, *, fields: dict[str, object]
    ) -> LessonModule:
        module = await self.get_module_or_404(module_id)
        for key, value in fields.items():
            setattr(module, key, value)
        await self.db.commit()
        await self.db.refresh(module)
        return module

    async def set_module_published(
        self, module_id: uuid.UUID, *, published: bool
    ) -> LessonModule:
        """Publish or withdraw a whole module (RF-47).

        Its lessons are not touched: a draft lesson inside a module being
        published stays a draft, and withdrawing a module hides everything under
        it without erasing which lessons were ready (RN-33).
        """
        module = await self.get_module_or_404(module_id)
        module.is_published = published
        await self.db.commit()
        await self.db.refresh(module)
        return module

    async def delete_module(self, module_id: uuid.UUID, *, confirm: bool) -> None:
        """Delete a module with everything under it (RN-36).

        The count travels in ``details`` so the interface can say «se perderán 3
        lecciones» with the exact number instead of a vague warning. The cascade
        itself is the database's job, declared on the foreign keys.
        """
        module = await self.get_module_or_404(module_id)
        lesson_count = len(module.lessons)
        if not confirm:
            raise ConflictError(
                self._deletion_warning(lesson_count),
                code="CONFIRMATION_REQUIRED",
                details={"lessons": lesson_count},
            )
        await self.repo.delete_module(module)
        await self.db.commit()

    @staticmethod
    def _deletion_warning(lesson_count: int) -> str:
        if lesson_count == 0:
            return "El módulo se eliminará. Confirma para continuar."
        if lesson_count == 1:
            return "Al eliminar el módulo se perderá 1 lección con sus recursos."
        return (
            f"Al eliminar el módulo se perderán {lesson_count} lecciones con sus recursos."
        )

    async def reorder_modules(self, ids: list[uuid.UUID]) -> list[LessonModule]:
        modules = await self.repo.list_modules()
        self._apply_order(modules, ids, subject="módulos")
        await self.db.commit()
        return sorted(modules, key=lambda module: module.position)

    # --- Lessons ---

    async def get_lesson_or_404(self, lesson_id: uuid.UUID) -> Lesson:
        lesson = await self.repo.get_lesson(lesson_id)
        if lesson is None:
            raise NotFoundError("Lección no encontrada.")
        return lesson

    async def get_visible_lesson(
        self, lesson_id: uuid.UUID, *, can_edit: bool
    ) -> tuple[Lesson, LessonModule]:
        """A lesson and the module it belongs to, or 404 (RN-33).

        The module wins: a published lesson inside a draft module is not
        visible, and «no visible» has to read exactly like «no existe». Anything
        else would let somebody enumerate identifiers to find out what is being
        prepared.
        """
        lesson = await self.get_lesson_or_404(lesson_id)
        module = await self.get_module_or_404(lesson.module_id)
        if not can_edit and not (module.is_published and lesson.is_published):
            raise NotFoundError("Lección no encontrada.")
        return lesson, module

    async def create_lesson(
        self,
        module_id: uuid.UUID,
        *,
        title: str,
        description: str | None,
        created_by: uuid.UUID,
    ) -> Lesson:
        """Born a draft, at the end of its module (RF-49, RF-50)."""
        await self.get_module_or_404(module_id)
        lesson = Lesson(
            module_id=module_id,
            title=title,
            description=description,
            position=await self.repo.next_lesson_position(module_id),
            is_published=False,
            created_by=created_by,
        )
        self.repo.add(lesson)
        await self.db.commit()
        await self.db.refresh(lesson)
        return lesson

    async def update_lesson(
        self, lesson_id: uuid.UUID, *, fields: dict[str, object]
    ) -> Lesson:
        lesson = await self.get_lesson_or_404(lesson_id)
        for key, value in fields.items():
            setattr(lesson, key, value)
        await self.db.commit()
        await self.db.refresh(lesson)
        return lesson

    async def set_lesson_published(
        self, lesson_id: uuid.UUID, *, published: bool
    ) -> Lesson:
        """Publish or withdraw one lesson (RF-47).

        Publishing it does not publish its module, and that is the point of
        RN-33: an editor gets to finish lesson by lesson and release the module
        when the whole thing is ready.
        """
        lesson = await self.get_lesson_or_404(lesson_id)
        lesson.is_published = published
        await self.db.commit()
        await self.db.refresh(lesson)
        return lesson

    async def delete_lesson(self, lesson_id: uuid.UUID) -> None:
        """Takes its resources with it, by cascade on the foreign key.

        No confirmation is demanded here: RN-36 asks for it when a whole module
        would disappear, and a lesson holds links, not lessons. The interface
        still asks before firing.
        """
        lesson = await self.get_lesson_or_404(lesson_id)
        await self.repo.delete_lesson(lesson)
        await self.db.commit()

    async def reorder_lessons(
        self, module_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> list[Lesson]:
        module = await self.get_module_or_404(module_id)
        lessons = list(module.lessons)
        self._apply_order(lessons, ids, subject="lecciones del módulo")
        await self.db.commit()
        return sorted(lessons, key=lambda lesson: lesson.position)

    # --- Resources ---

    async def add_resource(
        self, lesson_id: uuid.UUID, *, type: ResourceType, title: str, url: str
    ) -> LessonResource:
        """Link material, never store it (RN-34)."""
        await self.get_lesson_or_404(lesson_id)
        resource = LessonResource(
            lesson_id=lesson_id,
            type=type,
            title=title,
            url=url,
            position=await self.repo.next_resource_position(lesson_id),
        )
        self.repo.add(resource)
        await self.db.commit()
        await self.db.refresh(resource)
        return resource

    async def delete_resource(self, resource_id: uuid.UUID) -> None:
        resource = await self.repo.get_resource(resource_id)
        if resource is None:
            raise NotFoundError("Recurso no encontrado.")
        await self.repo.delete_resource(resource_id)
        await self.db.commit()

    async def reorder_resources(
        self, lesson_id: uuid.UUID, ids: list[uuid.UUID]
    ) -> list[LessonResource]:
        lesson = await self.get_lesson_or_404(lesson_id)
        resources = list(lesson.resources)
        self._apply_order(resources, ids, subject="recursos de la lección")
        await self.db.commit()
        return sorted(resources, key=lambda resource: resource.position)

    # --- Ordering ---

    @staticmethod
    def _apply_order(
        rows: list[Orderable], ids: list[uuid.UUID], *, subject: str
    ) -> None:
        """Rewrite positions to 0..n-1 in the order given (RF-50).

        The list has to name every element exactly once. Accepting a partial one
        would mean guessing where the rest go, and the guess would be wrong
        precisely when it matters: when a second editor added something while
        this order was being dragged into place.
        """
        by_id = {row.id: row for row in rows}
        if set(ids) != set(by_id):
            raise ValidationError(
                f"La lista de orden debe incluir exactamente los {subject} que existen."
            )
        for position, row_id in enumerate(ids):
            by_id[row_id].position = position
