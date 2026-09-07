"""HTTP endpoints for projects (api-contract.md 3).

No queries and no business rules here: the router picks a guard, calls the
service and shapes the response.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    require_global_role,
    require_project_permission,
)
from app.core.enums import GlobalRole, ProjectStatus, TaskStatus
from app.core.pagination import Pagination
from app.modules.projects.models import ProjectRole
from app.modules.projects.schemas import (
    MyRole,
    ProjectCreate,
    ProjectDetail,
    ProjectListItem,
    ProjectsPage,
    ProjectUpdate,
    TaskCounts,
)
from app.modules.projects.service import ProjectContext, ProjectsService
from app.modules.tasks.service import TasksService
from app.modules.users.models import User

router = APIRouter(prefix="/projects", tags=["projects"])


def _my_role(role: ProjectRole | None) -> MyRole | None:
    if role is None:
        return None
    return MyRole(id=role.id, name=role.name, color=role.color)


async def _detail(db: AsyncSession, ctx: ProjectContext) -> ProjectDetail:
    """Assemble the project detail, board tallies included.

    The tallies are asked of the tasks service *here*, in the router, and not
    from ``projects.service``. The allowed dependency runs ``tasks → projects``
    (architecture.md 2), so the projects service stays unaware that tasks exist
    and only this HTTP layer knows both. Nothing is stored either way: the counts
    are a GROUP BY on every read (data-model.md 8).
    """
    project = ctx.project
    service = ProjectsService(db)
    counts = await TasksService(db).count_by_status(project.id)
    return ProjectDetail(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        start_date=project.start_date,
        archived_at=project.archived_at,
        member_count=await service.count_members(project.id),
        task_counts=TaskCounts(
            **{status.value: counts.get(status, 0) for status in TaskStatus}
        ),
        my_permissions=sorted(ctx.permissions),
        my_role=_my_role(await service.get_member_role(ctx)),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("", response_model=ProjectsPage)
async def list_projects(
    status_filter: ProjectStatus | None = Query(default=None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectsPage:
    projects, total, counts, roles = await ProjectsService(db).list_projects(
        user=current_user,
        pagination=Pagination(page=page, size=size),
        status=status_filter,
    )
    return ProjectsPage(
        items=[
            ProjectListItem(
                id=project.id,
                name=project.name,
                description=project.description,
                status=project.status,
                start_date=project.start_date,
                member_count=counts.get(project.id, 0),
                my_role=_my_role(roles.get(project.id)),
                created_at=project.created_at,
            )
            for project in projects
        ],
        total=total,
        page=page,
        size=size,
    )


@router.post("", response_model=ProjectDetail, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    current_user: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    """Only a global ADMIN creates projects (RN-13)."""
    service = ProjectsService(db)
    project = await service.create_project(
        name=body.name,
        description=body.description,
        start_date=body.start_date,
        leader_user_id=body.leader_user_id,
        created_by=current_user,
    )
    ctx = await service.get_context(project.id, current_user)
    assert ctx is not None  # the creator is a global ADMIN, so a context exists
    return await _detail(db, ctx)


@router.get("/{project_id}", response_model=ProjectDetail)
async def get_project(
    ctx: ProjectContext = Depends(require_project_permission("task.view")),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    return await _detail(db, ctx)


@router.patch("/{project_id}", response_model=ProjectDetail)
async def update_project(
    body: ProjectUpdate,
    ctx: ProjectContext = Depends(require_project_permission("project.edit")),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    await ProjectsService(db).update_project(ctx, fields=body.model_dump(exclude_unset=True))
    return await _detail(db, ctx)


@router.post("/{project_id}/archive", response_model=ProjectDetail)
async def archive_project(
    ctx: ProjectContext = Depends(require_project_permission("project.archive")),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    """Archive the project (RF-18). It stays fully readable and stops accepting
    every kind of modification, plus every notification (RN-15, RN-16)."""
    await ProjectsService(db).set_archived(ctx, archived=True)
    return await _detail(db, ctx)


@router.post("/{project_id}/unarchive", response_model=ProjectDetail)
async def unarchive_project(
    ctx: ProjectContext = Depends(require_project_permission("project.archive")),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    await ProjectsService(db).set_archived(ctx, archived=False)
    return await _detail(db, ctx)
