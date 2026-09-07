"""Business rules for projects, project roles and memberships.

This module owns the authorization core of the platform. Two things matter more
than the rest:

* ``get_context`` resolves a user's permissions in a project on every request.
  Nothing is cached and nothing travels inside the JWT, so a role edit takes
  effect on the very next call (RN-22).
* ``create_project`` builds the project, its three system roles with their
  permissions, and the leader's membership inside a single transaction. A
  half-created project would be a project nobody can administer.

Transactions are opened and committed here, never in the repository or the
router.
"""

import datetime
import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import GlobalRole, ProjectStatus, UserStatus
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.pagination import Pagination
from app.modules.projects.constants import (
    LEADER_ROLE_NAME,
    PROJECT_ADMIN_PERMISSION,
    SYSTEM_ROLES,
    VIEW_PERMISSION,
)
from app.modules.projects.models import (
    Permission,
    Project,
    ProjectMember,
    ProjectRole,
    ProjectRolePermission,
)
from app.modules.projects.repository import ProjectsRepository
from app.modules.users.models import User
from app.modules.users.service import UsersService

# What a global ADMIN holds in a project they do not belong to.
#
# RN-01 denies the global ADMIN write access inside a project, while RN-14 ends
# with "El ADMIN siempre puede reasignar el liderazgo". Read access alone would
# make the second sentence impossible: if the only leader of a project were
# deactivated, nobody could ever administer that project again. So the ADMIN gets
# universal reading plus exactly the two permissions leadership reassignment
# needs — never task work, which is what RN-01 is protecting.
ADMIN_IMPLICIT_PERMISSIONS: frozenset[str] = frozenset(
    {VIEW_PERMISSION, "member.add", "role.assign"}
)


@dataclass(frozen=True)
class ProjectContext:
    """Everything an authorized request needs about a project, resolved once by
    the dependency so services never look it up again."""

    project: Project
    user: User
    member: ProjectMember | None
    permissions: frozenset[str]

    @property
    def project_id(self) -> uuid.UUID:
        return self.project.id

    @property
    def is_archived(self) -> bool:
        return self.project.status == ProjectStatus.ARCHIVED

    def has(self, permission: str) -> bool:
        return permission in self.permissions


class ProjectsService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = ProjectsRepository(db)
        self.users = UsersService(db)

    # --- Permission catalog ---

    async def list_permissions(self) -> list[Permission]:
        return await self.repo.list_permissions()

    # --- Context resolution ---

    async def get_context(
        self, project_id: uuid.UUID, user: User
    ) -> ProjectContext | None:
        """Resolve the user's standing in a project.

        Returns None when the project does not exist *or* when the user has no
        business knowing that it does; the caller turns both into a 404, so a
        stranger cannot tell one case from the other.
        """
        project = await self.repo.get_project(project_id)
        if project is None:
            return None

        member = await self.repo.get_member(project_id, user.id)
        permissions: set[str] = set()
        if member is not None:
            permissions = await self.repo.get_member_permission_codes(project_id, user.id)
        elif user.global_role != GlobalRole.ADMIN:
            return None

        if user.global_role == GlobalRole.ADMIN:
            permissions |= ADMIN_IMPLICIT_PERMISSIONS

        return ProjectContext(
            project=project,
            user=user,
            member=member,
            permissions=frozenset(permissions),
        )

    # --- Projects ---

    async def create_project(
        self,
        *,
        name: str,
        description: str | None,
        start_date: datetime.date | None,
        leader_user_id: uuid.UUID,
        created_by: User,
    ) -> Project:
        """Create a project with its three system roles and its first leader, all
        in one transaction (RF-13, RF-14, RN-13)."""
        leader = await self.users.get_or_404(leader_user_id)
        if leader.status != UserStatus.ACTIVE:
            raise ValidationError("El líder designado debe ser un usuario activo.")

        project = Project(
            name=name.strip(),
            description=description,
            start_date=start_date,
            status=ProjectStatus.ACTIVE,
            created_by=created_by.id,
        )
        self.repo.add(project)
        await self.db.flush()

        leader_role: ProjectRole | None = None
        for spec in SYSTEM_ROLES:
            role = ProjectRole(
                project_id=project.id,
                name=spec.name,
                color=spec.color,
                is_system=True,
                created_by=None,  # nobody authored the defaults (RN-19)
                permissions=[
                    ProjectRolePermission(permission_code=code)
                    for code in sorted(spec.permissions)
                ],
            )
            self.repo.add(role)
            if spec.name == LEADER_ROLE_NAME:
                leader_role = role
        await self.db.flush()

        assert leader_role is not None  # SYSTEM_ROLES always contains the leader
        self.repo.add(
            ProjectMember(
                project_id=project.id,
                user_id=leader.id,
                project_role_id=leader_role.id,
                added_by=created_by.id,
            )
        )
        await self.db.commit()
        return project

    async def list_projects(
        self,
        *,
        user: User,
        pagination: Pagination,
        status: ProjectStatus | None = None,
    ) -> tuple[list[Project], int, dict[uuid.UUID, int], dict[uuid.UUID, ProjectRole]]:
        """Projects the user can see, with member counts and the user's own role
        in each. A global ADMIN sees every project (RN-01)."""
        is_admin = user.global_role == GlobalRole.ADMIN
        projects, total = await self.repo.list_projects(
            member_user_id=None if is_admin else user.id,
            status=status,
            offset=pagination.offset,
            limit=pagination.limit,
        )
        project_ids = [p.id for p in projects]
        counts = await self.repo.count_members_by_project(project_ids)
        memberships = await self.repo.get_memberships(user.id, project_ids)
        roles = {pid: role for pid, (_, role) in memberships.items()}
        return projects, total, counts, roles

    async def get_member_role(self, ctx: ProjectContext) -> ProjectRole | None:
        if ctx.member is None:
            return None
        return await self.repo.get_role(ctx.member.project_role_id)

    async def count_members(self, project_id: uuid.UUID) -> int:
        return await self.repo.count_members(project_id)

    async def update_project(
        self,
        ctx: ProjectContext,
        *,
        fields: dict[str, object],
    ) -> Project:
        """Edit name, description and dates (RF-13, `project.edit`). Only the keys
        actually sent are applied, so a PATCH never blanks what it omits."""
        for key, value in fields.items():
            setattr(ctx.project, key, value)
        await self.db.commit()
        return ctx.project

    async def set_archived(self, ctx: ProjectContext, *, archived: bool) -> Project:
        """Archive or unarchive (RF-18, RN-15). Status and archived_at move
        together; the database check constraint would reject anything else."""
        if archived and ctx.is_archived:
            raise ConflictError("El proyecto ya está archivado.")
        if not archived and not ctx.is_archived:
            raise ConflictError("El proyecto no está archivado.")

        if archived:
            ctx.project.status = ProjectStatus.ARCHIVED
            ctx.project.archived_at = datetime.datetime.now(datetime.UTC)
        else:
            ctx.project.status = ProjectStatus.ACTIVE
            ctx.project.archived_at = None
        await self.db.commit()
        return ctx.project

    # --- Members ---

    async def list_members(
        self, ctx: ProjectContext
    ) -> list[tuple[ProjectMember, ProjectRole, User]]:
        rows = await self.repo.list_members(ctx.project_id)
        users = await self.users.get_many([member.user_id for member, _ in rows])
        return [(member, role, users[member.user_id]) for member, role in rows]

    # --- Cross-module queries ---
    #
    # Both return plain identifiers and strings rather than Project or User rows.
    # Another module (tasks, today) needs to know who belongs where without ever
    # touching this module's tables or its models (architecture.md 2).

    async def member_user_ids(self, project_id: uuid.UUID) -> set[uuid.UUID]:
        """Who is a member of this project, by id."""
        return await self.repo.member_user_ids(project_id)

    async def member_project_names(self, user_id: uuid.UUID) -> dict[uuid.UUID, str]:
        """Project id to project name, for every project the user belongs to.

        It is what a cross-project view needs to label its rows: "Mis tareas"
        shows the project each task comes from (RF-36).
        """
        return {
            project.id: project.name
            for project in await self.repo.list_member_projects(user_id)
        }

    async def add_member(
        self,
        ctx: ProjectContext,
        *,
        user_id: uuid.UUID,
        project_role_id: uuid.UUID,
    ) -> tuple[ProjectMember, ProjectRole, User]:
        """Add an existing platform user to the project (RF-15). New people are
        never invited from here: that is the admin's invitation flow."""
        role = await self._get_project_role_or_404(ctx.project_id, project_role_id)
        user = await self.users.get_or_404(user_id)
        if user.status != UserStatus.ACTIVE:
            raise ValidationError("Solo se pueden agregar usuarios activos.")

        member = ProjectMember(
            project_id=ctx.project_id,
            user_id=user.id,
            project_role_id=role.id,
            added_by=ctx.user.id,
        )
        self.repo.add(member)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            # The (project_id, user_id) uniqueness constraint: one role per user
            # per project (RN-03).
            raise ConflictError("El usuario ya es miembro del proyecto.") from exc

        await self.db.commit()
        return member, role, user

    async def remove_member(self, ctx: ProjectContext, *, user_id: uuid.UUID) -> None:
        """Remove a member (RF-16). Their tasks and submissions survive: only the
        membership goes away."""
        member = await self.repo.get_member(ctx.project_id, user_id)
        if member is None:
            raise NotFoundError("El usuario no es miembro de este proyecto.")

        await self._guard_last_project_admin(ctx.project_id, excluding_user_id=user_id)
        await self.repo.delete_member(member)
        await self.db.commit()

    async def change_member_role(
        self,
        ctx: ProjectContext,
        *,
        user_id: uuid.UUID,
        project_role_id: uuid.UUID,
    ) -> tuple[ProjectMember, ProjectRole, User]:
        """Change a member's project role (RF-17). One role per project, always."""
        member = await self.repo.get_member(ctx.project_id, user_id)
        if member is None:
            raise NotFoundError("El usuario no es miembro de este proyecto.")
        role = await self._get_project_role_or_404(ctx.project_id, project_role_id)

        if PROJECT_ADMIN_PERMISSION not in role.permission_codes:
            await self._guard_last_project_admin(
                ctx.project_id, excluding_user_id=user_id
            )

        member.project_role_id = role.id
        await self.db.commit()
        user = await self.users.get_or_404(user_id)
        return member, role, user

    # --- Roles ---

    async def list_roles(
        self, ctx: ProjectContext
    ) -> list[tuple[ProjectRole, int, User | None]]:
        roles = await self.repo.list_roles(ctx.project_id)
        counts = await self.repo.count_members_by_role(ctx.project_id)
        author_ids = [role.created_by for role in roles if role.created_by is not None]
        authors = await self.users.get_many(author_ids)
        return [
            (
                role,
                counts.get(role.id, 0),
                authors.get(role.created_by) if role.created_by else None,
            )
            for role in roles
        ]

    async def create_role(
        self,
        ctx: ProjectContext,
        *,
        name: str,
        color: str,
        permissions: list[str],
    ) -> tuple[ProjectRole, int, User | None]:
        """Create a custom role inside this project (RF-21, RN-18). It exists only
        here: roles are never shared between projects (RN-03, RF-23)."""
        codes = await self._validate_permission_selection(permissions)
        await self._guard_role_name_available(ctx.project_id, name)

        role = ProjectRole(
            project_id=ctx.project_id,
            name=name,
            color=color,
            is_system=False,
            created_by=ctx.user.id,  # RN-19
            permissions=[
                ProjectRolePermission(permission_code=code) for code in sorted(codes)
            ],
        )
        self.repo.add(role)
        await self.db.commit()
        return role, 0, ctx.user

    async def update_role(
        self,
        ctx: ProjectContext,
        *,
        role_id: uuid.UUID,
        name: str,
        color: str,
        permissions: list[str],
    ) -> tuple[ProjectRole, int, User | None]:
        """Edit a custom role. The change reaches its members on their next
        request, with no new sign-in (RN-22)."""
        role = await self._get_project_role_or_404(ctx.project_id, role_id)
        self._guard_not_system_role(role)

        codes = await self._validate_permission_selection(permissions)
        await self._guard_role_name_available(ctx.project_id, name, exclude_role_id=role.id)

        current = role.permission_codes
        # Same spirit as RN-14: stripping project.archive from the only role that
        # carries it would leave the project with nobody able to administer it.
        if PROJECT_ADMIN_PERMISSION in current and PROJECT_ADMIN_PERMISSION not in codes:
            holders = await self.repo.count_members_with_permission(
                ctx.project_id, PROJECT_ADMIN_PERMISSION
            )
            members_of_role = await self.repo.count_role_members(role.id)
            if members_of_role > 0 and holders - members_of_role <= 0:
                raise ConflictError(
                    "El proyecto quedaría sin nadie que pueda administrarlo.",
                    code="LAST_PROJECT_ADMIN",
                )

        role.name = name
        role.color = color
        await self.repo.remove_role_permissions(role.id, current - codes)
        await self.repo.add_role_permissions(role.id, codes - current)
        await self.db.commit()
        await self.db.refresh(role, ["permissions"])

        member_count = await self.repo.count_role_members(role.id)
        author = (
            (await self.users.get_many([role.created_by])).get(role.created_by)
            if role.created_by
            else None
        )
        return role, member_count, author

    async def delete_role(self, ctx: ProjectContext, *, role_id: uuid.UUID) -> None:
        """Delete a custom role. Reassign its members first (RF-24, RN-21)."""
        role = await self._get_project_role_or_404(ctx.project_id, role_id)
        self._guard_not_system_role(role)

        member_count = await self.repo.count_role_members(role.id)
        if member_count > 0:
            raise ConflictError(
                f"El rol tiene {member_count} "
                f"{'miembro asignado' if member_count == 1 else 'miembros asignados'}. "
                "Reasígnalos antes de eliminarlo.",
                code="ROLE_HAS_MEMBERS",
                details={"member_count": member_count},
            )

        await self.repo.delete_role(role)
        await self.db.commit()

    # --- Guards ---

    async def _get_project_role_or_404(
        self, project_id: uuid.UUID, role_id: uuid.UUID
    ) -> ProjectRole:
        role = await self.repo.get_role(role_id)
        # A role from another project is reported as missing, not as forbidden:
        # its existence is none of this project's business (RN-03, RN-04).
        if role is None or role.project_id != project_id:
            raise NotFoundError("Rol no encontrado en este proyecto.")
        return role

    @staticmethod
    def _guard_not_system_role(role: ProjectRole) -> None:
        if role.is_system:
            raise ConflictError(
                "Los roles predeterminados no se pueden editar ni eliminar.",
                code="SYSTEM_ROLE_IMMUTABLE",
            )

    async def _guard_role_name_available(
        self,
        project_id: uuid.UUID,
        name: str,
        *,
        exclude_role_id: uuid.UUID | None = None,
    ) -> None:
        existing = await self.repo.get_role_by_name(
            project_id, name, exclude_role_id=exclude_role_id
        )
        if existing is not None:
            raise ConflictError(
                f"Ya existe un rol llamado «{existing.name}» en este proyecto.",
                code="ROLE_NAME_TAKEN",
            )

    async def _validate_permission_selection(self, permissions: list[str]) -> set[str]:
        """RN-05: every role must be able to see the project. RN-06: no permission
        implies another, so the rest of the selection is taken literally."""
        codes = set(permissions)
        if VIEW_PERMISSION not in codes:
            raise ValidationError(
                f"El permiso «{VIEW_PERMISSION}» es obligatorio en todo rol.",
                details={"missing": [VIEW_PERMISSION]},
            )
        known = await self.repo.existing_permission_codes(codes)
        unknown = sorted(codes - known)
        if unknown:
            raise ValidationError(
                "El catálogo de permisos no incluye: " + ", ".join(unknown),
                details={"unknown": unknown},
            )
        return codes

    async def _guard_last_project_admin(
        self, project_id: uuid.UUID, *, excluding_user_id: uuid.UUID
    ) -> None:
        """RN-14: a project can never be left without a member holding
        project.archive."""
        remaining = await self.repo.count_members_with_permission(
            project_id, PROJECT_ADMIN_PERMISSION, exclude_user_id=excluding_user_id
        )
        if remaining == 0:
            raise ConflictError(
                "El proyecto quedaría sin nadie que pueda administrarlo. "
                "Designa antes a otro líder.",
                code="LAST_PROJECT_ADMIN",
            )
