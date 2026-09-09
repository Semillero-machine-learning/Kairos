"""The one endpoint that hangs off ``/resources/{resource_id}``.

A file of its own for a single route because that is what the path prefix asks
for, the same way the tasks module keeps ``comments_router`` apart. Creating a
resource lives with its lesson, in ``lessons_router``; only the deletion is
addressed by the resource's own identifier (api-contract.md 8).
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_lesson_editor
from app.modules.lessons.service import LessonsService
from app.modules.users.models import User

router = APIRouter(prefix="/resources", tags=["lessons"])


@router.delete("/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    resource_id: uuid.UUID,
    _editor: User = Depends(require_lesson_editor()),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Unlink, which is all there is to undo: the platform never held the file
    on the other end (RN-34)."""
    await LessonsService(db).delete_resource(resource_id)
