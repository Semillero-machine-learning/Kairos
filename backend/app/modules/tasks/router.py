"""The board endpoints, scoped to a project (api-contract.md 5).

No queries and no business rules here: the router picks a guard, calls the
service and shapes the response.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_project_permission
from app.core.enums import TaskPeriodicity, TaskStatus
from app.core.pagination import Pagination
from app.modules.projects.service import ProjectContext
from app.modules.tasks.presenters import task_read
from app.modules.tasks.schemas import TaskCreate, TaskRead, TasksPage
from app.modules.tasks.service import TasksService

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["tasks"])


@router.get("", response_model=TasksPage)
async def list_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    assignee_id: uuid.UUID | None = Query(default=None),
    periodicity: TaskPeriodicity | None = Query(default=None),
    overdue: bool = Query(default=False),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    ctx: ProjectContext = Depends(require_project_permission("task.view")),
    db: AsyncSession = Depends(get_db),
) -> TasksPage:
    """The board, with the four filters of RF-36.

    The default page is larger than elsewhere because this feeds five Kanban
    columns at once: a project of fifty tasks should arrive in one request.
    """
    views, total = await TasksService(db).list_tasks(
        ctx,
        pagination=Pagination(page=page, size=size),
        status=status_filter,
        assignee_id=assignee_id,
        periodicity=periodicity,
        overdue=overdue,
    )
    return TasksPage(
        items=[task_read(view) for view in views], total=total, page=page, size=size
    )


@router.post("", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(
    body: TaskCreate,
    ctx: ProjectContext = Depends(require_project_permission("task.create")),
    db: AsyncSession = Depends(get_db),
) -> TaskRead:
    """Create a task with its responsibles (RF-25, RF-27)."""
    view = await TasksService(db).create_task(
        ctx,
        title=body.title,
        description=body.description,
        periodicity=body.periodicity,
        due_date=body.due_date,
        assignee_ids=body.assignee_ids,
    )
    return task_read(view)
