"""Data access for the lesson catalog. Queries only, no decisions.

``list_modules`` deliberately fetches the whole tree with no visibility filter
and no text filter. Both of those are business rules — who may see a draft
(RN-32, RN-33) and what counts as a match for a search — and they belong in the
service. The cost of deciding them there instead of in SQL is loading a few rows
that get discarded: api-contract.md §8 already commits to returning the entire
tree in one request precisely because the catalog is decenas de módulos at most,
and RNF-04 says not to optimize past correct indexes at this scale.

The three levels come back in three queries thanks to the selectin loading
declared on the models, not in one query per lesson.
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.lessons.models import Lesson, LessonModule, LessonResource


class LessonsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, obj: object) -> None:
        self.db.add(obj)

    # --- Modules ---

    async def list_modules(self) -> list[LessonModule]:
        rows = await self.db.execute(select(LessonModule).order_by(LessonModule.position))
        return list(rows.scalars().unique().all())

    async def get_module(self, module_id: uuid.UUID) -> LessonModule | None:
        return await self.db.get(LessonModule, module_id)

    async def next_module_position(self) -> int:
        """One past the last, so a new module lands at the end of the catalog."""
        query = select(func.coalesce(func.max(LessonModule.position) + 1, 0))
        return (await self.db.execute(query)).scalar_one()

    async def delete_module(self, module: LessonModule) -> None:
        await self.db.delete(module)

    # --- Lessons ---

    async def get_lesson(self, lesson_id: uuid.UUID) -> Lesson | None:
        return await self.db.get(Lesson, lesson_id)

    async def next_lesson_position(self, module_id: uuid.UUID) -> int:
        query = select(func.coalesce(func.max(Lesson.position) + 1, 0)).where(
            Lesson.module_id == module_id
        )
        return (await self.db.execute(query)).scalar_one()

    async def delete_lesson(self, lesson: Lesson) -> None:
        await self.db.delete(lesson)

    # --- Resources ---

    async def get_resource(self, resource_id: uuid.UUID) -> LessonResource | None:
        return await self.db.get(LessonResource, resource_id)

    async def next_resource_position(self, lesson_id: uuid.UUID) -> int:
        query = select(func.coalesce(func.max(LessonResource.position) + 1, 0)).where(
            LessonResource.lesson_id == lesson_id
        )
        return (await self.db.execute(query)).scalar_one()

    async def delete_resource(self, resource_id: uuid.UUID) -> None:
        await self.db.execute(delete(LessonResource).where(LessonResource.id == resource_id))
