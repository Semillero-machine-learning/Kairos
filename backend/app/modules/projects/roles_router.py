"""HTTP endpoints for custom project roles (api-contract.md 4)."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_project_permission
from app.modules.projects.models import ProjectRole
from app.modules.projects.schemas import RoleRead, RoleWrite, UserRef
from app.modules.projects.service import ProjectContext, ProjectsService
from app.modules.users.models import User

router = APIRouter(prefix="/projects/{project_id}/roles", tags=["projects"])


def _role(role: ProjectRole, member_count: int, author: User | None) -> RoleRead:
    return RoleRead(
        id=role.id,
        project_id=role.project_id,
        name=role.name,
        color=role.color,
        is_system=role.is_system,
        permissions=sorted(role.permission_codes),
        created_by=(
            UserRef(id=author.id, full_name=author.full_name, email=author.email)
            if author is not None
            else None
        ),
        member_count=member_count,
        created_at=role.created_at,
    )


@router.get("", response_model=list[RoleRead])
async def list_roles(
    ctx: ProjectContext = Depends(require_project_permission("task.view")),
    db: AsyncSession = Depends(get_db),
) -> list[RoleRead]:
    rows = await ProjectsService(db).list_roles(ctx)
    return [_role(role, count, author) for role, count, author in rows]


@router.post("", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    body: RoleWrite,
    ctx: ProjectContext = Depends(require_project_permission("role.manage")),
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    """Create a custom role in this project (RF-21). It never leaves it (RF-23)."""
    role, count, author = await ProjectsService(db).create_role(
        ctx, name=body.name, color=body.color, permissions=body.permissions
    )
    return _role(role, count, author)


@router.patch("/{role_id}", response_model=RoleRead)
async def update_role(
    role_id: uuid.UUID,
    body: RoleWrite,
    ctx: ProjectContext = Depends(require_project_permission("role.manage")),
    db: AsyncSession = Depends(get_db),
) -> RoleRead:
    role, count, author = await ProjectsService(db).update_role(
        ctx,
        role_id=role_id,
        name=body.name,
        color=body.color,
        permissions=body.permissions,
    )
    return _role(role, count, author)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_permission("role.manage")),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ProjectsService(db).delete_role(ctx, role_id=role_id)
