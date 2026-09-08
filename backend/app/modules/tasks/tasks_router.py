"""Endpoints that hang off a task id (api-contract.md 5 and 6).

Split from router.py because these routes carry no ``project_id``: the project
is resolved from the task by ``require_task_permission``, which is the same
guard underneath.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_task_permission
from app.modules.tasks.presenters import comment_read, submission_read, task_read
from app.modules.tasks.schemas import (
    AssigneeAdd,
    CommentCreate,
    CommentRead,
    SubmissionCreate,
    SubmissionRead,
    TaskRead,
    TaskStatusChange,
    TaskUpdate,
)
from app.modules.tasks.service import TaskContext, TasksService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(
    tctx: TaskContext = Depends(require_task_permission("task.view")),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    return task_read(await TasksService(db).build_view(tctx.task))


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    body: TaskUpdate,
    tctx: TaskContext = Depends(require_task_permission("task.edit_any")),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    """Edit title, description, periodicity and due date. The status is not here:
    it moves through the state machine."""
    view = await TasksService(db).update_task(
        tctx, fields=body.model_dump(exclude_unset=True)
    )
    return task_read(view)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    tctx: TaskContext = Depends(require_task_permission("task.delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft delete (RF-37): the row and its submissions stay (RN-17)."""
    await TasksService(db).delete_task(tctx)


@router.post("/{task_id}/assignees", response_model=TaskRead)
async def add_assignee(
    body: AssigneeAdd,
    tctx: TaskContext = Depends(require_task_permission("task.assign")),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    """Answers with the whole task, not just the new responsible: it is what the
    board has to redraw."""
    view = await TasksService(db).add_assignee(tctx, user_id=body.user_id)
    return task_read(view)


@router.delete("/{task_id}/assignees/{user_id}", response_model=TaskRead)
async def remove_assignee(
    user_id: uuid.UUID,
    tctx: TaskContext = Depends(require_task_permission("task.assign")),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    view = await TasksService(db).remove_assignee(tctx, user_id=user_id)
    return task_read(view)


@router.post("/{task_id}/status", response_model=TaskRead)
async def change_status(
    body: TaskStatusChange,
    # Only task.view is demanded: who may make each move is the transition
    # table's business (RN-10). ``mutates`` is what still refuses the write on an
    # archived project (RN-15).
    tctx: TaskContext = Depends(require_task_permission("task.view", mutates=True)),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    view = await TasksService(db).change_status(tctx, target=body.status)
    return task_read(view)


@router.get("/{task_id}/submissions", response_model=list[SubmissionRead])
async def list_submissions(
    tctx: TaskContext = Depends(require_task_permission("task.view")),
    db: AsyncSession = Depends(get_db),
) -> list[SubmissionRead]:
    """The whole history, newest first (RF-34)."""
    views = await TasksService(db).list_submissions(tctx)
    return [submission_read(view) for view in views]


@router.post(
    "/{task_id}/submissions",
    response_model=SubmissionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_submission(
    body: SubmissionCreate,
    tctx: TaskContext = Depends(require_task_permission("task.view", mutates=True)),
    db: AsyncSession = Depends(get_db),
) -> SubmissionRead:
    """Register the work handed in. Moves the task to IN_REVIEW in the same
    transaction (RF-31). Being a responsible is what authorizes it, not a
    permission of the catalog."""
    view, _task = await TasksService(db).create_submission(
        tctx, description=body.description, commit_url=body.commit_url
    )
    return submission_read(view)


@router.get("/{task_id}/comments", response_model=list[CommentRead])
async def list_comments(
    tctx: TaskContext = Depends(require_task_permission("task.view")),
    db: AsyncSession = Depends(get_db),
) -> list[CommentRead]:
    """The thread of the task, oldest first (RF-35)."""
    views = await TasksService(db).list_comments(tctx)
    return [comment_read(view) for view in views]


@router.post(
    "/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    body: CommentCreate,
    tctx: TaskContext = Depends(require_task_permission("task.comment")),
    db: AsyncSession = Depends(get_db),
) -> CommentRead:
    return comment_read(await TasksService(db).create_comment(tctx, body=body.body))
