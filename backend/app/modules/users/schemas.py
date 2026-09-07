"""Pydantic schemas for the users module."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.enums import GlobalRole, UserStatus


class UserListItem(BaseModel):
    """A row in GET /users. Admins see the full shape; other users see only
    id/full_name/email (the reduced assignment-selector view), with the
    admin-only fields left null."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    global_role: GlobalRole | None = None
    status: UserStatus | None = None
    created_at: datetime | None = None


class UsersPage(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    size: int


class UserDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    global_role: GlobalRole
    status: UserStatus
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChangeRoleRequest(BaseModel):
    global_role: GlobalRole


class ChangeStatusRequest(BaseModel):
    status: UserStatus
