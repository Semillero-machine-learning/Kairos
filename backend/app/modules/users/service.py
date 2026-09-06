"""Business rules for users.

Mutating building blocks (create_user, set_role, set_status) flush but do not
commit, so a composing service — CLI, or auth accepting an invitation — owns the
transaction and commits once. Use-case methods that are the top of their own
call chain commit explicitly.
"""

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import GlobalRole, UserStatus
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.modules.users.models import User
from app.modules.users.repository import UsersRepository

PASSWORD_MIN_LENGTH = 10


class UsersService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UsersRepository(db)

    async def create_user(
        self,
        *,
        full_name: str,
        email: str,
        password_hash: str,
        global_role: GlobalRole,
    ) -> User:
        """Create a user. Flushes (surfacing the email uniqueness constraint as a
        domain error) but does not commit."""
        user = User(
            full_name=full_name,
            email=email,
            password_hash=password_hash,
            global_role=global_role,
            status=UserStatus.ACTIVE,
        )
        self.repo.add(user)
        try:
            await self.db.flush()
        except IntegrityError as exc:
            await self.db.rollback()
            raise ConflictError(
                "El correo ya está registrado.", code="EMAIL_ALREADY_REGISTERED"
            ) from exc
        return user

    async def get_or_404(self, user_id: uuid.UUID) -> User:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("Usuario no encontrado.")
        return user

    @staticmethod
    def validate_password_strength(password: str) -> None:
        if len(password) < PASSWORD_MIN_LENGTH:
            raise ValidationError(
                f"La contraseña debe tener al menos {PASSWORD_MIN_LENGTH} caracteres."
            )
