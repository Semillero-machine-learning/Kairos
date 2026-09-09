"""Service views to response schemas.

Three routers answer with the same shapes, so the mapping lives once here
instead of being copied into each of them. Pure translation: no queries, no
decisions.
"""

from app.modules.lessons.models import Lesson, LessonModule, LessonResource
from app.modules.lessons.schemas import (
    LessonDetail,
    LessonModuleRead,
    LessonRead,
    LessonResourceRead,
)
from app.modules.lessons.service import CatalogModule


def resource_read(resource: LessonResource) -> LessonResourceRead:
    return LessonResourceRead(
        id=resource.id,
        type=resource.type,
        title=resource.title,
        url=resource.url,
        position=resource.position,
    )


def lesson_read(lesson: Lesson) -> LessonRead:
    """The count of resources, not the resources: the tree is for browsing.

    ``lesson.resources`` is already loaded by the selectin on the model, so this
    is a ``len`` over rows in memory and not a query per lesson.
    """
    return LessonRead(
        id=lesson.id,
        module_id=lesson.module_id,
        title=lesson.title,
        description=lesson.description,
        position=lesson.position,
        is_published=lesson.is_published,
        resource_count=len(lesson.resources),
    )


def lesson_detail(lesson: Lesson, module: LessonModule) -> LessonDetail:
    """The lesson's own screen: every link, in the order the editor set.

    ``module_title`` comes from the module the service already resolved, so a
    direct link to a lesson can name where it belongs without a second request.
    """
    return LessonDetail(
        id=lesson.id,
        module_id=lesson.module_id,
        module_title=module.title,
        title=lesson.title,
        description=lesson.description,
        position=lesson.position,
        is_published=lesson.is_published,
        resources=[resource_read(resource) for resource in lesson.resources],
        created_at=lesson.created_at,
        updated_at=lesson.updated_at,
    )


def module_read(module: LessonModule, lessons: list[Lesson]) -> LessonModuleRead:
    """Lessons come in as a parameter, never from ``module.lessons``.

    The service decided which ones this viewer may see (RN-32, RN-33); reading
    the relationship here instead would quietly undo that decision.
    """
    return LessonModuleRead(
        id=module.id,
        title=module.title,
        description=module.description,
        position=module.position,
        is_published=module.is_published,
        lessons=[lesson_read(lesson) for lesson in lessons],
        created_at=module.created_at,
        updated_at=module.updated_at,
    )


def catalog_read(catalog: list[CatalogModule]) -> list[LessonModuleRead]:
    return [module_read(entry.module, entry.lessons) for entry in catalog]
