"""HTTP endpoints for lesson modules (api-contract.md 8).

No queries and no business rules here: the router picks a guard, turns the
caller into the primitives the service takes, and shapes the response.

Two things are decided at this layer and nowhere else:

* **Who is asking**, reduced to ``can_edit_lessons(user.global_role)``. The
  service never sees a ``User``, which is what keeps the lessons module free of
  imports from the rest of the application.
* **404 for a module that does not exist**, plain and simple. Unlike projects,
  there is nothing to hide here: the catalog is one, it is public to every
  authenticated user, and refusing to say whether a module exists would protect
  nothing.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_lesson_editor
from app.modules.lessons.presenters import catalog_read, module_read
from app.modules.lessons.schemas import (
    LessonModuleCreate,
    LessonModuleRead,
    LessonModuleUpdate,
    PublishBody,
    ReorderBody,
)
from app.modules.lessons.service import LessonsService, can_edit_lessons
from app.modules.users.models import User

router = APIRouter(prefix="/lesson-modules", tags=["lessons"])


@router.get("", response_model=list[LessonModuleRead])
async def list_lesson_modules(
    q: str | None = Query(default=None, max_length=150),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LessonModuleRead]:
    """The whole catalog in one request (RF-51).

    Not paginated, and that is deliberate: api-contract.md §8 settles it —
    decenas de módulos as a ceiling, so paging would be ceremony without a
    reason. What each viewer gets back is not the same tree: drafts are for
    editors only (RN-32, RN-33).
    """
    catalog = await LessonsService(db).list_catalog(
        can_edit=can_edit_lessons(current_user.global_role), query=q
    )
    return catalog_read(catalog)


@router.post("", response_model=LessonModuleRead, status_code=status.HTTP_201_CREATED)
async def create_lesson_module(
    body: LessonModuleCreate,
    editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> LessonModuleRead:
    module = await LessonsService(db).create_module(
        title=body.title, description=body.description, created_by=editor.id
    )
    return module_read(module, [])


@router.post("/reorder", response_model=list[LessonModuleRead])
async def reorder_lesson_modules(
    body: ReorderBody,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> list[LessonModuleRead]:
    """Declared before the routes with ``{module_id}`` so «reorder» is never
    read as an identifier (RF-50)."""
    service = LessonsService(db)
    modules = await service.reorder_modules(body.ids)
    return [module_read(module, list(module.lessons)) for module in modules]


@router.patch("/{module_id}", response_model=LessonModuleRead)
async def update_lesson_module(
    module_id: uuid.UUID,
    body: LessonModuleUpdate,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> LessonModuleRead:
    module = await LessonsService(db).update_module(
        module_id, fields=body.model_dump(exclude_unset=True)
    )
    return module_read(module, list(module.lessons))


@router.post("/{module_id}/publish", response_model=LessonModuleRead)
async def publish_lesson_module(
    module_id: uuid.UUID,
    body: PublishBody,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> LessonModuleRead:
    """Publish or withdraw (RF-47). The body says which, so there is one
    endpoint for one decision instead of two that can drift apart."""
    module = await LessonsService(db).set_module_published(
        module_id, published=body.published
    )
    return module_read(module, list(module.lessons))


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lesson_module(
    module_id: uuid.UUID,
    confirm: bool = Query(default=False),
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Without ``?confirm=true`` this answers 409 saying how many lessons would
    be lost (RN-36). The count is in the ``details`` of the error."""
    await LessonsService(db).delete_module(module_id, confirm=confirm)
