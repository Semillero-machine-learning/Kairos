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
from app.modules.tasks.service import (
    CommentContext,
    SubmissionContext,
    TaskContext,
    TasksService,
)
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


def require_lesson_editor() -> Callable[[User], Awaitable[User]]:
    """The single guard of the lesson catalog (RN-31).

    Named instead of spelling out the two roles at each of the three routers:
    RN-31 is one rule and it should have one place to change. A project leader
    whose global role is MEMBER is refused here, and gets a 403 rather than the
    404 that project-scoped routes return — there is no membership to hide, the
    catalog is one and everybody knows it exists.
    """
    return require_global_role(GlobalRole.ADMIN, GlobalRole.LESSON_EDITOR)


def _authorize(ctx: ProjectContext, permission: str, *, mutates: bool) -> None:
    """The single authorization decision, shared by both project-scoped guards.

    An archived project still answers reads: RF-18 says it can be consulted in
    full, and RN-15 restricts it to read-only, not to no access. So the archived
    check keys off whether the request *writes*, not off the permission alone —
    a status change asks for nothing more than ``task.view`` and still has to be
    refused on an archived project.
    """
    if permission not in ctx.permissions:
        raise ForbiddenError(f"Se requiere el permiso «{permission}».")
    if (
        ctx.project.status == ProjectStatus.ARCHIVED
        and mutates
        and permission != PROJECT_ADMIN_PERMISSION
    ):
        raise ConflictError(
            "El proyecto está archivado y no admite modificaciones.",
            code="PROJECT_ARCHIVED",
        )


def _writes_by_default(permission: str) -> bool:
    return permission not in READ_ONLY_PERMISSIONS


def require_project_permission(
    permission: str,
    *,
    mutates: bool | None = None,
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

    ``mutates`` overrides that last judgement for an endpoint whose permission
    does not describe what it does; it defaults to "anything but a read-only
    permission writes".
    """
    writes = _writes_by_default(permission) if mutates is None else mutates

    async def dependency(
        project_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> ProjectContext:
        ctx = await ProjectsService(db).get_context(project_id, user)
        if ctx is None:
            raise NotFoundError("Proyecto no encontrado.")
        _authorize(ctx, permission, mutates=writes)
        return ctx

    return dependency


async def _task_context(
    task_id: uuid.UUID,
    user: User,
    db: AsyncSession,
    permission: str,
    *,
    writes: bool,
    missing_message: str,
) -> TaskContext:
    """Resolve a task and the caller's standing in its project, or 404.

    Shared by the three task-scoped guards below. The message differs because a
    404 has to name what the caller asked for — a submission, a comment — and
    never leak which of "it does not exist" and "you cannot see it" was true.
    """
    task = await TasksService(db).get_or_404(task_id)
    ctx = await ProjectsService(db).get_context(task.project_id, user)
    if ctx is None:
        raise NotFoundError(missing_message)
    _authorize(ctx, permission, mutates=writes)
    return TaskContext(task=task, project=ctx)


def require_task_permission(
    permission: str,
    *,
    mutates: bool | None = None,
) -> Callable[..., Awaitable[TaskContext]]:
    """The same guard, for the endpoints that hang off ``/tasks/{task_id}``.

    Those routes carry no ``project_id``, so the project is resolved from the
    task and handed to the very same ``get_context``: one path for permission
    resolution, with its 404-instead-of-403 and its archived check in one place
    rather than two that can drift apart.

    A task in a project the user cannot see is reported as missing, exactly like
    a task that does not exist — the 404 must not tell a stranger which of the
    two it was.

    ``mutates=True`` is what ``POST /tasks/{id}/status`` and ``POST
    /tasks/{id}/submissions`` need: they ask only for ``task.view``, because who
    may make the move is the state machine's business, but they are writes and an
    archived project has to refuse them (RN-15).
    """
    writes = _writes_by_default(permission) if mutates is None else mutates

    async def dependency(
        task_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> TaskContext:
        return await _task_context(
            task_id,
            user,
            db,
            permission,
            writes=writes,
            missing_message="Tarea no encontrada.",
        )

    return dependency

def require_submission_permission(
    permission: str,
    *,
    mutates: bool | None = None,
) -> Callable[..., Awaitable[SubmissionContext]]:
    """Guard for the routes that hang off ``/submissions/{submission_id}``.

    The chain is submission → task → project, and the authorization decision at
    the end is the same ``_authorize`` every other guard uses, so the archived
    check and the 404-instead-of-403 hold here too without being written again.

    ``PATCH /submissions/{id}`` asks only for ``task.view``: being the author is
    what authorizes it (RN-12), and that is a business rule the service owns,
    not an entry in the permission catalog.
    """
    writes = _writes_by_default(permission) if mutates is None else mutates

    async def dependency(
        submission_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> SubmissionContext:
        submission = await TasksService(db).get_submission_or_404(submission_id)
        tctx = await _task_context(
            submission.task_id,
            user,
            db,
            permission,
            writes=writes,
            missing_message="Entrega no encontrada.",
        )
        return SubmissionContext(submission=submission, task_ctx=tctx)

    return dependency


def require_comment_permission(
    permission: str,
    *,
    mutates: bool | None = None,
) -> Callable[..., Awaitable[CommentContext]]:
    """Guard for ``/comments/{comment_id}``.

    Both routes ask for ``task.view`` with ``mutates=True`` rather than for
    ``task.comment``: who may edit or delete a comment is RN-11 — the author, or
    a moderator with ``task.delete`` — and the service decides that. Demanding
    ``task.comment`` here would lock a moderator whose custom role can delete but
    not write out of moderating, and would stop someone whose role just lost
    ``task.comment`` from deleting what they had already said.
    """
    writes = _writes_by_default(permission) if mutates is None else mutates

    async def dependency(
        comment_id: uuid.UUID,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> CommentContext:
        comment = await TasksService(db).get_comment_or_404(comment_id)
        tctx = await _task_context(
            comment.task_id,
            user,
            db,
            permission,
            writes=writes,
            missing_message="Comentario no encontrado.",
        )
        return CommentContext(comment=comment, task_ctx=tctx)

    return dependency
