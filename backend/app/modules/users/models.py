"""SQLAlchemy models for the users module.

Enum types and the set_updated_at() trigger are created by migrations; the
models reference them with create_type=False so nothing is emitted twice.
"""

import enum
import uuid
from datetime import datetime

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.dialects.postgresql import ENUM as PGEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class GlobalRole(enum.StrEnum):
    ADMIN = "ADMIN"
    LESSON_EDITOR = "LESSON_EDITOR"
    MEMBER = "MEMBER"


class UserStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


global_role_enum = PGEnum(
    GlobalRole,
    name="global_role",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)
user_status_enum = PGEnum(
    UserStatus,
    name="user_status",
    create_type=False,
    values_callable=lambda e: [m.value for m in e],
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    full_name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(nullable=False)
    global_role: Mapped[GlobalRole] = mapped_column(
        global_role_enum, nullable=False, server_default=GlobalRole.MEMBER.value
    )
    status: Mapped[UserStatus] = mapped_column(
        user_status_enum, nullable=False, server_default=UserStatus.ACTIVE.value
    )
    last_login_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(nullable=False, server_default=func.now())
