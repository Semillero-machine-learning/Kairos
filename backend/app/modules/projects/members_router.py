"""HTTP endpoints for project membership (api-contract.md 4).

Split from router.py because members and roles are their own resource trees; the
prefix keeps them under the project they belong to.
"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_project_permission
from app.modules.projects.models import ProjectMember, ProjectRole
from app.modules.projects.schemas import (
    MemberAdd,
    MemberRead,
    MemberRoleChange,
    MyRole,
    UserRef,
)
from app.modules.projects.service import ProjectContext, ProjectsService
from app.modules.users.models import User

router = APIRouter(prefix="/projects/{project_id}/members", tags=["projects"])


def _member(member: ProjectMember, role: ProjectRole, user: User) -> MemberRead:
    return MemberRead(
        user=UserRef(id=user.id, full_name=user.full_name, email=user.email),
        role=MyRole(id=role.id, name=role.name, color=role.color),
        joined_at=member.joined_at,
    )


@router.get("", response_model=list[MemberRead])
async def list_members(
    ctx: ProjectContext = Depends(require_project_permission("task.view")),
    db: AsyncSession = Depends(get_db),
) -> list[MemberRead]:
    rows = await ProjectsService(db).list_members(ctx)
    return [_member(member, role, user) for member, role, user in rows]


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    body: MemberAdd,
    ctx: ProjectContext = Depends(require_project_permission("member.add")),
    db: AsyncSession = Depends(get_db),
) -> MemberRead:
    """Add an existing platform user (RF-15). Inviting new people to the platform
    is a separate, admin-only flow."""
    member, role, user = await ProjectsService(db).add_member(
        ctx, user_id=body.user_id, project_role_id=body.project_role_id
    )
    return _member(member, role, user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: uuid.UUID,
    ctx: ProjectContext = Depends(require_project_permission("member.remove")),
    db: AsyncSession = Depends(get_db),
) -> None:
    await ProjectsService(db).remove_member(ctx, user_id=user_id)


@router.patch("/{user_id}/role", response_model=MemberRead)
async def change_member_role(
    user_id: uuid.UUID,
    body: MemberRoleChange,
    ctx: ProjectContext = Depends(require_project_permission("role.assign")),
    db: AsyncSession = Depends(get_db),
) -> MemberRead:
    member, role, user = await ProjectsService(db).change_member_role(
        ctx, user_id=user_id, project_role_id=body.project_role_id
    )
    return _member(member, role, user)
