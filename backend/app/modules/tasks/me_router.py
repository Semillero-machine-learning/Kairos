"""«Mis tareas» across every project (api-contract.md 5, RF-36).

The only task route with no project guard: it is scoped by the user themself,
and the service limits it to projects they belong to.
"""

import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.enums import TaskStatus
from app.core.pagination import Pagination
from app.modules.tasks.presenters import my_task_read
from app.modules.tasks.schemas import MyTasksPage
from app.modules.tasks.service import TasksService
from app.modules.users.models import User

router = APIRouter(prefix="/me/tasks", tags=["tasks"])


@router.get("", response_model=MyTasksPage)
async def list_my_tasks(
    status_filter: TaskStatus | None = Query(default=None, alias="status"),
    due_before: datetime.date | None = Query(default=None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MyTasksPage:
    rows, total = await TasksService(db).list_my_tasks(
        current_user.id,
        pagination=Pagination(page=page, size=size),
        status=status_filter,
        due_before=due_before,
    )
    return MyTasksPage(
        items=[my_task_read(row) for row in rows], total=total, page=page, size=size
    )
