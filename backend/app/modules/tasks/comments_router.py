"""Endpoints that hang off a comment id (api-contract.md 6).

The two routes under ``/tasks/{task_id}/comments`` live in ``tasks_router.py``
with the rest of the task-scoped ones; these two are here because they resolve
the project through the comment.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_comment_permission
from app.modules.tasks.presenters import comment_read
from app.modules.tasks.schemas import CommentRead, CommentUpdate
from app.modules.tasks.service import CommentContext, TasksService

router = APIRouter(prefix="/comments", tags=["tasks"])


@router.patch("/{comment_id}", response_model=CommentRead)
async def update_comment(
    body: CommentUpdate,
    cctx: CommentContext = Depends(require_comment_permission("task.view", mutates=True)),
    db: AsyncSession = Depends(get_db),
) -> CommentRead:
    """Only the author (RN-11); the service is what decides that."""
    return comment_read(await TasksService(db).update_comment(cctx, body=body.body))


@router.delete("/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    cctx: CommentContext = Depends(require_comment_permission("task.view", mutates=True)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """The author, or a moderator holding ``task.delete`` (RN-11). Soft delete."""
    await TasksService(db).delete_comment(cctx)
