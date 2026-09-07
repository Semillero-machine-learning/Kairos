"""HTTP endpoints for user administration. No business logic or queries here.

GET /users is available to any authenticated user in a reduced form (id, name,
email of active users) for assignment selectors; the rest of the group requires
the global ADMIN role.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_global_role
from app.core.enums import GlobalRole, UserStatus
from app.core.pagination import Pagination
from app.modules.users.models import User
from app.modules.users.schemas import (
    ChangeRoleRequest,
    ChangeStatusRequest,
    UserDetail,
    UserListItem,
    UsersPage,
)
from app.modules.users.service import UsersService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UsersPage)
async def list_users(
    search: str | None = None,
    status: UserStatus | None = None,
    global_role: GlobalRole | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsersPage:
    is_admin = current_user.global_role == GlobalRole.ADMIN
    service = UsersService(db)

    if is_admin:
        users, total = await service.list_users(
            pagination=Pagination(page=page, size=size),
            search=search,
            status=status,
            global_role=global_role,
        )
        items = [UserListItem.model_validate(u) for u in users]
    else:
        # Reduced selector view: only active users, only id/name/email.
        users, total = await service.list_users(
            pagination=Pagination(page=page, size=size),
            search=search,
            status=UserStatus.ACTIVE,
        )
        items = [
            UserListItem(id=u.id, full_name=u.full_name, email=u.email) for u in users
        ]

    return UsersPage(items=items, total=total, page=page, size=size)


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: uuid.UUID,
    _: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserDetail:
    user = await UsersService(db).get_or_404(user_id)
    return UserDetail.model_validate(user)


@router.patch("/{user_id}/role", response_model=UserDetail)
async def change_role(
    user_id: uuid.UUID,
    body: ChangeRoleRequest,
    _: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserDetail:
    user = await UsersService(db).change_global_role(user_id, body.global_role)
    return UserDetail.model_validate(user)


@router.patch("/{user_id}/status", response_model=UserDetail)
async def change_status(
    user_id: uuid.UUID,
    body: ChangeStatusRequest,
    _: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserDetail:
    user = await UsersService(db).set_status(user_id, body.status)
    return UserDetail.model_validate(user)
