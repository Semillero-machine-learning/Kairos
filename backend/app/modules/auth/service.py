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
from app.core.enums import GlobalRole, UserStatus
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.security import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.integrations.email import EmailClient, render_email
from app.modules.auth.models import (
    Invitation,
    InvitationStatus,
    PasswordResetToken,
    RefreshToken,
)
from app.modules.auth.repository import AuthRepository
from app.modules.users.models import User
from app.modules.users.service import UsersService

INVITATION_TTL_DAYS = 7
PASSWORD_RESET_TTL_HOURS = 1

ROLE_LABELS: dict[GlobalRole, str] = {
    GlobalRole.ADMIN: "Administrador",
    GlobalRole.LESSON_EDITOR: "Editor de Lecciones",
    GlobalRole.MEMBER: "Miembro",
}

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
        self.email = EmailClient()

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

    # --- Invitations ---

    def _invite_url(self, raw_token: str) -> str:
        return f"{self.settings.frontend_url.rstrip('/')}/invitacion/{raw_token}"

    async def _send_invitation_email(
        self, invitation: Invitation, raw_token: str
    ) -> None:
        html = render_email(
            "invitation.html",
            role_label=ROLE_LABELS.get(invitation.global_role, invitation.global_role.value),
            invite_url=self._invite_url(raw_token),
            expires_at=invitation.expires_at.date().isoformat(),
        )
        await self.email.send(
            to=str(invitation.email),
            subject="Invitación al Semillero de Machine Learning",
            html=html,
        )

    async def create_invitation(
        self, admin: User, email: str, global_role: GlobalRole
    ) -> tuple[Invitation, str]:
        """Create a single-use invitation (RF-02). A registered email is rejected
        (EB-02); an existing pending invitation for the email is revoked and
        replaced (EB-03)."""
        if await self.users.email_exists(email):
            raise ConflictError(
                "El correo ya está registrado.", code="EMAIL_ALREADY_REGISTERED"
            )

        existing = await self.repo.get_pending_invitation_by_email(email)
        if existing is not None:
            existing.status = InvitationStatus.REVOKED
            await self.db.flush()

        raw = generate_opaque_token()
        invitation = Invitation(
            email=email,
            global_role=global_role,
            token_hash=hash_opaque_token(raw),
            expires_at=datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS),
            status=InvitationStatus.PENDING,
            invited_by=admin.id,
        )
        self.repo.add(invitation)
        await self.db.commit()
        await self._send_invitation_email(invitation, raw)
        return invitation, self._invite_url(raw)

    async def resend_invitation(self, invitation_id: uuid.UUID) -> tuple[Invitation, str]:
        """Reissue the token, invalidating the previous one (RF-04)."""
        invitation = await self.repo.get_invitation_by_id(invitation_id)
        if invitation is None:
            raise NotFoundError("Invitación no encontrada.")
        if invitation.status != InvitationStatus.PENDING:
            raise ConflictError("La invitación no está pendiente.")

        raw = generate_opaque_token()
        invitation.token_hash = hash_opaque_token(raw)
        invitation.expires_at = datetime.now(UTC) + timedelta(days=INVITATION_TTL_DAYS)
        await self.db.commit()
        await self._send_invitation_email(invitation, raw)
        return invitation, self._invite_url(raw)

    async def revoke_invitation(self, invitation_id: uuid.UUID) -> None:
        invitation = await self.repo.get_invitation_by_id(invitation_id)
        if invitation is None:
            raise NotFoundError("Invitación no encontrada.")
        if invitation.status != InvitationStatus.PENDING:
            raise ConflictError("La invitación ya no está pendiente.")
        invitation.status = InvitationStatus.REVOKED
        await self.db.commit()

    async def list_invitations(
        self, status: InvitationStatus | None = None
    ) -> list[Invitation]:
        return await self.repo.list_invitations(status=status)

    async def validate_invitation_token(self, raw_token: str) -> Invitation:
        """Resolve a usable (PENDING, not expired) invitation from a raw token.

        A replaced/revoked or unknown token is reported as 404 so the old link
        simply stops working without revealing whether the email has an account
        (EB-01). Expiry is assigned lazily on read.
        """
        invitation = await self.repo.get_invitation_by_token_hash(hash_opaque_token(raw_token))
        if invitation is None or invitation.status == InvitationStatus.REVOKED:
            raise NotFoundError("La invitación no existe o ya no es válida.")
        if invitation.status == InvitationStatus.ACCEPTED:
            raise ConflictError(
                "La invitación ya fue utilizada.", code="INVITATION_ALREADY_USED"
            )
        if invitation.expires_at <= datetime.now(UTC):
            if invitation.status != InvitationStatus.EXPIRED:
                invitation.status = InvitationStatus.EXPIRED
                await self.db.commit()
            raise ConflictError("La invitación expiró.", code="INVITATION_EXPIRED")
        return invitation

    async def accept_invitation(
        self,
        raw_token: str,
        full_name: str,
        password: str,
        *,
        user_agent: str | None = None,
    ) -> IssuedTokens:
        """Create the account, invalidate the token and sign the user in (RF-03)."""
        invitation = await self.validate_invitation_token(raw_token)
        self.users.validate_password_strength(password)

        user = await self.users.create_user(
            full_name=full_name,
            email=str(invitation.email),
            password_hash=hash_password(password),
            global_role=invitation.global_role,
        )
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.now(UTC)
        invitation.accepted_user_id = user.id

        access = create_access_token(user.id, user.global_role)
        refresh = self._issue_refresh_token(user.id, user_agent)
        await self.db.commit()
        return IssuedTokens(user=user, access_token=access, refresh_token=refresh)

    # --- Password reset ---

    def _reset_url(self, raw_token: str) -> str:
        return f"{self.settings.frontend_url.rstrip('/')}/restablecer/{raw_token}"

    async def request_password_reset(
        self, email: str, *, user_agent: str | None = None
    ) -> None:
        """Issue a reset token and email it, only for an existing active account.
        The endpoint always responds identically, so this never signals whether
        the email exists (RN-41)."""
        user = await self.users.get_by_email(email)
        if user is None or user.status != UserStatus.ACTIVE:
            return

        raw = generate_opaque_token()
        self.repo.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_opaque_token(raw),
                expires_at=datetime.now(UTC) + timedelta(hours=PASSWORD_RESET_TTL_HOURS),
                user_agent=user_agent,
            )
        )
        await self.db.commit()

        html = render_email("password_reset.html", reset_url=self._reset_url(raw))
        await self.email.send(
            to=str(user.email),
            subject="Restablecer tu contraseña",
            html=html,
        )

    async def confirm_password_reset(self, raw_token: str, new_password: str) -> None:
        """Set a new password from a single-use reset token, then revoke every
        refresh token (RN-41, RN-42)."""
        record = await self.repo.get_reset_by_hash(hash_opaque_token(raw_token))
        now = datetime.now(UTC)
        if record is None or record.used_at is not None or record.expires_at <= now:
            raise ValidationError(
                "El enlace de restablecimiento no es válido o expiró.",
                code="INVALID_RESET_TOKEN",
            )

        self.users.validate_password_strength(new_password)
        user = await self.users.get_by_id(record.user_id)
        if user is None:
            raise ValidationError(
                "El enlace de restablecimiento no es válido o expiró.",
                code="INVALID_RESET_TOKEN",
            )

        self.users.set_password(user, hash_password(new_password))
        record.used_at = now
        await self.repo.revoke_all_refresh_tokens(user.id, when=now)
        await self.db.commit()

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
