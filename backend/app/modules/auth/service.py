"""Auth business rules: login, rotating refresh tokens and logout.

Refresh tokens rotate on every use (RN-43): a use issues a new token and revokes
the old one. Presenting an already-revoked token is treated as theft and revokes
every session of that user. The transaction is owned and committed here.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.enums import UserStatus
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.modules.auth.models import RefreshToken
from app.modules.auth.repository import AuthRepository
from app.modules.users.models import User
from app.modules.users.service import UsersService

# Identical response whether credentials are wrong or the account is disabled,
# so login never reveals which emails exist (RF-05).
_INVALID_CREDENTIALS_MESSAGE = "Correo o contraseña incorrectos."
# A well-formed hash used to equalize timing when the email does not exist.
_DUMMY_HASH = hash_password("timing-equalizer-not-a-real-password")


@dataclass
class IssuedTokens:
    user: User
    access_token: str
    refresh_token: str


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = AuthRepository(db)
        self.users = UsersService(db)
        self.settings = get_settings()

    def _issue_refresh_token(self, user_id: uuid.UUID, user_agent: str | None) -> str:
        raw = generate_opaque_token()
        now = datetime.now(UTC)
        self.repo.add(
            RefreshToken(
                user_id=user_id,
                token_hash=hash_opaque_token(raw),
                expires_at=now + timedelta(days=self.settings.jwt_refresh_ttl_days),
                user_agent=user_agent,
            )
        )
        return raw

    async def login(
        self, email: str, password: str, *, user_agent: str | None = None
    ) -> IssuedTokens:
        user = await self.users.get_by_email(email)
        if user is None:
            verify_password(password, _DUMMY_HASH)  # equalize timing
            raise AuthenticationError(_INVALID_CREDENTIALS_MESSAGE)
        if user.status != UserStatus.ACTIVE or not verify_password(
            password, user.password_hash
        ):
            raise AuthenticationError(_INVALID_CREDENTIALS_MESSAGE)

        access = create_access_token(user.id, user.global_role)
        refresh = self._issue_refresh_token(user.id, user_agent)
        await self.users.touch_last_login(user, when=datetime.now(UTC))
        await self.db.commit()
        return IssuedTokens(user=user, access_token=access, refresh_token=refresh)

    async def refresh(
        self, raw_token: str, *, user_agent: str | None = None
    ) -> IssuedTokens:
        now = datetime.now(UTC)
        record = await self.repo.get_refresh_by_hash(hash_opaque_token(raw_token))
        if record is None:
            raise AuthenticationError("La sesión no es válida.")

        if record.revoked_at is not None:
            # Reuse of a revoked token: revoke every session of the user (RN-43).
            await self.repo.revoke_all_refresh_tokens(record.user_id, when=now)
            await self.db.commit()
            raise AuthenticationError("La sesión no es válida.")

        if record.expires_at <= now:
            raise AuthenticationError("La sesión expiró.")

        user = await self.users.get_by_id(record.user_id)
        if user is None or user.status != UserStatus.ACTIVE:
            await self.repo.revoke_all_refresh_tokens(record.user_id, when=now)
            await self.db.commit()
            raise AuthenticationError("La sesión no es válida.")

        record.revoked_at = now
        access = create_access_token(user.id, user.global_role)
        refresh = self._issue_refresh_token(user.id, user_agent)
        await self.db.commit()
        return IssuedTokens(user=user, access_token=access, refresh_token=refresh)

    async def change_password(
        self, user: User, current_password: str, new_password: str
    ) -> None:
        """Change the password after verifying the current one, then revoke every
        refresh token so other sessions must sign in again (RN-42)."""
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("La contraseña actual no es correcta.")
        self.users.validate_password_strength(new_password)
        self.users.set_password(user, hash_password(new_password))
        await self.repo.revoke_all_refresh_tokens(user.id, when=datetime.now(UTC))
        await self.db.commit()

    async def logout(self, user: User, raw_token: str) -> None:
        """Revoke the given refresh token if it belongs to the user. Idempotent."""
        record = await self.repo.get_refresh_by_hash(hash_opaque_token(raw_token))
        if record is not None and record.user_id == user.id and record.revoked_at is None:
            record.revoked_at = datetime.now(UTC)
            await self.db.commit()

    @property
    def access_expires_in(self) -> int:
        return self.settings.jwt_access_ttl_minutes * 60
