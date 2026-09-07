"""Data access for the auth module: invitations and token records.

Queries only; no business conditions. Rotation, reuse detection and expiry
decisions live in the service.
"""

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import (
    Invitation,
    InvitationStatus,
    PasswordResetToken,
    RefreshToken,
)


class AuthRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(self, obj: object) -> None:
        self.db.add(obj)

    # --- Refresh tokens ---

    async def get_refresh_by_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_all_refresh_tokens(self, user_id: uuid.UUID, *, when: datetime) -> None:
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=when)
        )

    # --- Invitations ---

    async def get_invitation_by_id(self, invitation_id: uuid.UUID) -> Invitation | None:
        return await self.db.get(Invitation, invitation_id)

    async def get_invitation_by_token_hash(self, token_hash: str) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation).where(Invitation.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    async def get_pending_invitation_by_email(self, email: str) -> Invitation | None:
        result = await self.db.execute(
            select(Invitation).where(
                Invitation.email == email,
                Invitation.status == InvitationStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def list_invitations(
        self, *, status: InvitationStatus | None = None
    ) -> list[Invitation]:
        query = select(Invitation).order_by(Invitation.created_at.desc())
        if status is not None:
            query = query.where(Invitation.status == status)
        return list((await self.db.execute(query)).scalars().all())

    # --- Password reset tokens ---

    async def get_reset_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()
