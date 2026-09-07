"""Data access for projects, roles and members. Queries only, no decisions."""

import uuid

from sqlalchemy import Select, delete, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ProjectStatus
from app.modules.projects.models import (
    Permission,
    Project,
    ProjectMember,
    ProjectRole,
    ProjectRolePermission,
)


class ProjectsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, obj: object) -> None:
        self.db.add(obj)

    # --- Permission catalog ---

    async def list_permissions(self) -> list[Permission]:
        rows = await self.db.execute(select(Permission).order_by(Permission.code))
        return list(rows.scalars().all())

    async def existing_permission_codes(self, codes: set[str]) -> set[str]:
        rows = await self.db.execute(
            select(Permission.code).where(Permission.code.in_(codes))
        )
        return set(rows.scalars().all())

    # --- Projects ---

    async def get_project(self, project_id: uuid.UUID) -> Project | None:
        return await self.db.get(Project, project_id)

    def _project_list_query(self, status: ProjectStatus | None) -> Select:
        query = select(Project)
        if status is not None:
            query = query.where(Project.status == status)
        return query

    async def list_projects(
        self,
        *,
        member_user_id: uuid.UUID | None,
        status: ProjectStatus | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Project], int]:
        """Projects visible to a user. ``member_user_id=None`` lists every
        project, which is what a global ADMIN gets (RN-01, read access)."""
        query = self._project_list_query(status)
        count_query = select(func.count()).select_from(self._project_list_query(status).subquery())

        if member_user_id is not None:
            membership = exists().where(
                ProjectMember.project_id == Project.id,
                ProjectMember.user_id == member_user_id,
            )
            query = query.where(membership)
            count_query = select(func.count()).select_from(
                self._project_list_query(status).where(membership).subquery()
            )

        total = (await self.db.execute(count_query)).scalar_one()
        rows = await self.db.execute(
            query.order_by(Project.created_at.desc()).offset(offset).limit(limit)
        )
        return list(rows.scalars().all()), total

    async def count_members(self, project_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
        )
        return result.scalar_one()

    async def count_members_by_project(
        self, project_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, int]:
        """Member counts for a page of projects, in one query. Nothing is stored:
        the count is always derived (data-model.md 8)."""
        if not project_ids:
            return {}
        rows = await self.db.execute(
            select(ProjectMember.project_id, func.count())
            .where(ProjectMember.project_id.in_(project_ids))
            .group_by(ProjectMember.project_id)
        )
        return {project_id: count for project_id, count in rows.all()}

    # --- Membership and permission resolution ---

    async def get_member(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectMember | None:
        result = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_member_permission_codes(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> set[str]:
        """The permission codes a user holds in a project, read on every request
        so that a role edit takes effect immediately (RN-22)."""
        result = await self.db.execute(
            select(ProjectRolePermission.permission_code)
            .join(ProjectRole, ProjectRole.id == ProjectRolePermission.project_role_id)
            .join(ProjectMember, ProjectMember.project_role_id == ProjectRole.id)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        return set(result.scalars().all())

    async def get_memberships(
        self, user_id: uuid.UUID, project_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[ProjectMember, ProjectRole]]:
        """The user's membership and role for a page of projects, in one query."""
        if not project_ids:
            return {}
        result = await self.db.execute(
            select(ProjectMember, ProjectRole)
            .join(ProjectRole, ProjectRole.id == ProjectMember.project_role_id)
            .where(
                ProjectMember.user_id == user_id,
                ProjectMember.project_id.in_(project_ids),
            )
        )
        return {member.project_id: (member, role) for member, role in result.all()}

    async def member_user_ids(self, project_id: uuid.UUID) -> set[uuid.UUID]:
        rows = await self.db.execute(
            select(ProjectMember.user_id).where(ProjectMember.project_id == project_id)
        )
        return set(rows.scalars().all())

    async def list_member_projects(self, user_id: uuid.UUID) -> list[Project]:
        """Every project the user belongs to, unpaginated. With ten active
        projects this is one small query, and it is what the cross-project views
        need before they can ask another module anything."""
        rows = await self.db.execute(
            select(Project)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(ProjectMember.user_id == user_id)
            .order_by(Project.name)
        )
        return list(rows.scalars().all())

    async def list_members(self, project_id: uuid.UUID) -> list[tuple[ProjectMember, ProjectRole]]:
        result = await self.db.execute(
            select(ProjectMember, ProjectRole)
            .join(ProjectRole, ProjectRole.id == ProjectMember.project_role_id)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.joined_at)
        )
        return [(member, role) for member, role in result.all()]

    async def count_members_with_permission(
        self,
        project_id: uuid.UUID,
        permission_code: str,
        *,
        exclude_user_id: uuid.UUID | None = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(ProjectMember)
            .join(ProjectRole, ProjectRole.id == ProjectMember.project_role_id)
            .join(
                ProjectRolePermission,
                ProjectRolePermission.project_role_id == ProjectRole.id,
            )
            .where(
                ProjectMember.project_id == project_id,
                ProjectRolePermission.permission_code == permission_code,
            )
        )
        if exclude_user_id is not None:
            query = query.where(ProjectMember.user_id != exclude_user_id)
        return (await self.db.execute(query)).scalar_one()

    async def delete_member(self, member: ProjectMember) -> None:
        await self.db.delete(member)

    # --- Roles ---

    async def get_role(self, role_id: uuid.UUID) -> ProjectRole | None:
        # A select rather than db.get(), so the selectin loader always brings the
        # permission rows along: reading them lazily under asyncio would fail.
        result = await self.db.execute(select(ProjectRole).where(ProjectRole.id == role_id))
        return result.scalar_one_or_none()

    async def list_roles(self, project_id: uuid.UUID) -> list[ProjectRole]:
        result = await self.db.execute(
            select(ProjectRole)
            .where(ProjectRole.project_id == project_id)
            .order_by(ProjectRole.is_system.desc(), ProjectRole.created_at)
        )
        return list(result.scalars().all())

    async def get_role_by_name(
        self, project_id: uuid.UUID, name: str, *, exclude_role_id: uuid.UUID | None = None
    ) -> ProjectRole | None:
        query = select(ProjectRole).where(
            ProjectRole.project_id == project_id,
            func.lower(ProjectRole.name) == name.lower(),
        )
        if exclude_role_id is not None:
            query = query.where(ProjectRole.id != exclude_role_id)
        return (await self.db.execute(query)).scalar_one_or_none()

    async def count_role_members(self, role_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_role_id == role_id)
        )
        return result.scalar_one()

    async def count_members_by_role(self, project_id: uuid.UUID) -> dict[uuid.UUID, int]:
        rows = await self.db.execute(
            select(ProjectMember.project_role_id, func.count())
            .where(ProjectMember.project_id == project_id)
            .group_by(ProjectMember.project_role_id)
        )
        return {role_id: count for role_id, count in rows.all()}

    async def add_role_permissions(self, role_id: uuid.UUID, codes: set[str]) -> None:
        for code in sorted(codes):
            self.db.add(
                ProjectRolePermission(project_role_id=role_id, permission_code=code)
            )

    async def remove_role_permissions(self, role_id: uuid.UUID, codes: set[str]) -> None:
        if not codes:
            return
        await self.db.execute(
            delete(ProjectRolePermission).where(
                ProjectRolePermission.project_role_id == role_id,
                ProjectRolePermission.permission_code.in_(codes),
            )
        )

    async def delete_role(self, role: ProjectRole) -> None:
        await self.db.delete(role)
