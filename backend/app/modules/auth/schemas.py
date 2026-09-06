"""Pydantic schemas for the auth module."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import GlobalRole


class UserRead(BaseModel):
    """Public shape of a user, embedded in the token response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    global_role: GlobalRole


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
