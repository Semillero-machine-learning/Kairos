"""Pydantic schemas for the auth module."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import GlobalRole, UserStatus


class UserRead(BaseModel):
    """Public shape of a user, embedded in the token response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    global_role: GlobalRole


class MeRead(BaseModel):
    """Full profile of the user in session (GET /auth/me)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    global_role: GlobalRole
    status: UserStatus
    last_login_at: datetime | None
    created_at: datetime


class UpdateMeRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


# --- Invitations ---


class InvitationCreate(BaseModel):
    email: EmailStr
    global_role: GlobalRole


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    global_role: GlobalRole
    status: str
    expires_at: datetime
    created_at: datetime
    accepted_at: datetime | None = None


class InvitationCreatedResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    global_role: GlobalRole
    status: str
    expires_at: datetime
    invite_url: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserRead
