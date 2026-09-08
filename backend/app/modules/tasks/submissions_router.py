"""Endpoints that hang off a submission id (api-contract.md 6).

Separate file for the same reason ``tasks_router.py`` is separate from
``router.py``: these routes carry neither ``project_id`` nor ``task_id``, so the
project is reached through the submission by ``require_submission_permission``.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_submission_permission
from app.modules.tasks.presenters import submission_read
from app.modules.tasks.schemas import (
    SubmissionRead,
    SubmissionReview,
    SubmissionUpdate,
)
from app.modules.tasks.service import SubmissionContext, TasksService

router = APIRouter(prefix="/submissions", tags=["tasks"])


@router.patch("/{submission_id}", response_model=SubmissionRead)
async def update_submission(
    body: SubmissionUpdate,
    # task.view, because the author is who is allowed here (RN-12) and that is a
    # business rule, not a permission. ``mutates`` keeps an archived project
    # read-only all the same (RN-15).
    sctx: SubmissionContext = Depends(
        require_submission_permission("task.view", mutates=True)
    ),
    db: AsyncSession = Depends(get_db),
) -> SubmissionRead:
    """Fix your own submission while it is still waiting for review (RN-12)."""
    view = await TasksService(db).update_submission(
        sctx, fields=body.model_dump(exclude_unset=True)
    )
    return submission_read(view)


@router.post("/{submission_id}/review", response_model=SubmissionRead)
async def review_submission(
    body: SubmissionReview,
    sctx: SubmissionContext = Depends(require_submission_permission("task.review")),
    db: AsyncSession = Depends(get_db),
) -> SubmissionRead:
    """Approve (task to DONE) or send back (task to IN_PROGRESS), RF-33.

    Answers with the submission rather than the task: the task's new state is
    implied by the review, and what the reviewer's screen redraws is the
    submission history. The board refetches on navigation.
    """
    view, _task = await TasksService(db).review_submission(
        sctx, approved=body.approved, comment=body.comment
    )
    return submission_read(view)
