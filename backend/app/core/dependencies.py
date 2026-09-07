"""Shared FastAPI dependencies: current user and global-role guards.

get_current_user loads the user from the database on every request and rejects
disabled accounts, so a role or status change takes effect immediately without
waiting for the access token to expire (RN-22, RN-44). require_project_permission
resolves project permissions the same way, per request and never from the token.
"""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.enums import GlobalRole, ProjectStatus, UserStatus
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
)
from app.core.security import decode_access_token
from app.modules.projects.constants import (
    PROJECT_ADMIN_PERMISSION,
    READ_ONLY_PERMISSIONS,
)
from app.modules.projects.service import ProjectContext, ProjectsService
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


def require_project_permission(
    permission: str,
) -> Callable[..., Awaitable[ProjectContext]]:
    """Guard every project-scoped endpoint (architecture.md 3).

    Three details carry the design:

    * **404, never 403, for a non-member.** A 403 would confirm that the project
      exists, which is exactly what a stranger should not learn.
    * **The archived check lives here**, once, instead of being repeated in every
      endpoint and forgotten in one of them (RN-15).
    * The permissions come from the database on this request. Nothing about
      project roles is read from the access token (RN-22).

    An archived project still answers reads: RF-18 says it can be consulted in
    full, and RN-15 restricts it to read-only, not to no access. The snippet in
    architecture.md 3 rejects everything but ``project.archive``, which would
    lock the project out of view entirely; business-rules.md wins, so reads and
    unarchiving pass and every other permission is refused.
    """

    async def dependency(
        project_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectContext:
        ctx = await ProjectsService(db).get_context(project_id, user)
        if ctx is None:
            raise NotFoundError("Proyecto no encontrado.")
        if permission not in ctx.permissions:
            raise ForbiddenError(f"Se requiere el permiso «{permission}».")
        if (
            ctx.project.status == ProjectStatus.ARCHIVED
            and permission not in READ_ONLY_PERMISSIONS
            and permission != PROJECT_ADMIN_PERMISSION
        ):
            raise ConflictError(
                "El proyecto está archivado y no admite modificaciones.",
                code="PROJECT_ARCHIVED",
            )
        return ctx

    return dependency
