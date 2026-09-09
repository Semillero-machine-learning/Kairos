"""HTTP endpoints that hang off ``/lessons/{lesson_id}`` (api-contract.md 8).

The reading route and the writing ones are together here because they share a
path, not because they share an audience: ``GET`` answers to any authenticated
user and everything else to an editor.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_lesson_editor
from app.modules.lessons.presenters import lesson_detail, lesson_read, resource_read
from app.modules.lessons.schemas import (
    LessonDetail,
    LessonRead,
    LessonResourceCreate,
    LessonResourceRead,
    LessonUpdate,
    PublishBody,
    ReorderBody,
)
from app.modules.lessons.service import LessonsService, can_edit_lessons
from app.modules.users.models import User

router = APIRouter(prefix="/lessons", tags=["lessons"])


@router.get("/{lesson_id}", response_model=LessonDetail)
async def get_lesson(
    lesson_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LessonDetail:
    """The lesson with its links, if this person is allowed to see it.

    A draft — or a published lesson inside a draft module — answers 404 and not
    403 (RN-33). Here the 404 is not about hiding who owns what, as it is in
    projects: it is about not letting somebody walk the identifiers to find out
    what the editors are preparing.
    """
    lesson, module = await LessonsService(db).get_visible_lesson(
        lesson_id, can_edit=can_edit_lessons(current_user.global_role)
    )
    return lesson_detail(lesson, module)


@router.patch("/{lesson_id}", response_model=LessonRead)
async def update_lesson(
    lesson_id: uuid.UUID,
    body: LessonUpdate,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> LessonRead:
    lesson = await LessonsService(db).update_lesson(
        lesson_id, fields=body.model_dump(exclude_unset=True)
    )
    return lesson_read(lesson)


@router.post("/{lesson_id}/publish", response_model=LessonRead)
async def publish_lesson(
    lesson_id: uuid.UUID,
    body: PublishBody,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> LessonRead:
    """Publishing a lesson does not publish its module (RN-33).

    That is what lets an editor finish the material lesson by lesson and release
    the module only when the whole thing holds together.
    """
    lesson = await LessonsService(db).set_lesson_published(
        lesson_id, published=body.published
    )
    return lesson_read(lesson)


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson(
    lesson_id: uuid.UUID,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> None:
    """No ``?confirm=true`` here: RN-36 asks for the warning when a module and
    everything under it would go, and a lesson holds links, not lessons."""
    await LessonsService(db).delete_lesson(lesson_id)


@router.post(
    "/{lesson_id}/resources",
    response_model=LessonResourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_resource(
    lesson_id: uuid.UUID,
    body: LessonResourceCreate,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> LessonResourceRead:
    """The link is stored; the file is not, and never will be (RN-34)."""
    resource = await LessonsService(db).add_resource(
        lesson_id, type=body.type, title=body.title, url=body.url
    )
    return resource_read(resource)


@router.post("/{lesson_id}/resources/reorder", response_model=list[LessonResourceRead])
async def reorder_resources(
    lesson_id: uuid.UUID,
    body: ReorderBody,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> list[LessonResourceRead]:
    """The third level of ordering RF-50 asks for: the links inside a lesson."""
    resources = await LessonsService(db).reorder_resources(lesson_id, body.ids)
    return [resource_read(resource) for resource in resources]
