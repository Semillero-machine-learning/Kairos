"""Data access for users. Queries only: no business conditions live here."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import GlobalRole, User, UserStatus


class UsersRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def email_exists(self, email: str) -> bool:
        result = await self.db.execute(
            select(func.count()).select_from(User).where(User.email == email)
        )
        return result.scalar_one() > 0

    def add(self, user: User) -> None:
        self.db.add(user)

    async def list_users(
        self,
        *,
        search: str | None = None,
        status: UserStatus | None = None,
        global_role: GlobalRole | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        conditions = []
        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(User.full_name.ilike(pattern), User.email.ilike(pattern))
            )
        if status is not None:
            conditions.append(User.status == status)
        if global_role is not None:
            conditions.append(User.global_role == global_role)

        base = select(User)
        count_query = select(func.count()).select_from(User)
        for condition in conditions:
            base = base.where(condition)
            count_query = count_query.where(condition)

        total = (await self.db.execute(count_query)).scalar_one()
        rows = (
            await self.db.execute(
                base.order_by(User.created_at.desc()).offset(offset).limit(limit)
            )
        ).scalars().all()
        return list(rows), total

    async def count_active_admins(self, *, exclude_user_id: uuid.UUID | None = None) -> int:
        query = (
            select(func.count())
            .select_from(User)
            .where(User.global_role == GlobalRole.ADMIN, User.status == UserStatus.ACTIVE)
        )
        if exclude_user_id is not None:
            query = query.where(User.id != exclude_user_id)
        return (await self.db.execute(query)).scalar_one()
