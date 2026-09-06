"""Shared FastAPI dependencies: current user and global-role guards.

get_current_user loads the user from the database on every request and rejects
disabled accounts, so a role or status change takes effect immediately without
waiting for the access token to expire (RN-22, RN-44). require_project_permission
lives in the projects module and is added in Phase 2.
"""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import GlobalRole, UserStatus
from app.core.exceptions import AuthenticationError, ForbiddenError
from app.core.security import decode_access_token
from app.modules.users.models import User
from app.modules.users.repository import UsersRepository

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Se requiere autenticación.")

    payload = decode_access_token(credentials.credentials)
    subject = payload.get("sub")
    if not subject:
        raise AuthenticationError("Token inválido.")
    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise AuthenticationError("Token inválido.") from exc

    user = await UsersRepository(db).get_by_id(user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AuthenticationError("La sesión no es válida.")
    return user


def require_global_role(
    *roles: GlobalRole,
) -> Callable[[User], Awaitable[User]]:
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.global_role not in roles:
            raise ForbiddenError("No tienes permiso para esta operación.")
        return user

    return dependency
