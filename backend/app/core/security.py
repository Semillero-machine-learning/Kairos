"""Password hashing (Argon2id) and JWT issuing/validation.

The access token carries only the global role, never project permissions:
those are resolved per request so role changes take effect immediately (RN-22).
Opaque tokens (refresh, invitation, password reset) are random strings stored
only as SHA-256 hashes (RNF-05).
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings
from app.core.enums import GlobalRole
from app.core.exceptions import AuthenticationError

_hasher = PasswordHasher()  # argon2id by default
_JWT_ALGORITHM = "HS256"


# --- Passwords ---------------------------------------------------------------


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# --- Access tokens (JWT) -----------------------------------------------------


def create_access_token(user_id: uuid.UUID, global_role: GlobalRole) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "global_role": global_role.value,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.jwt_access_ttl_minutes)).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("La sesión expiró.") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Token inválido.") from exc


# --- Opaque tokens (refresh, invitation, password reset) ---------------------


def generate_opaque_token() -> str:
    """A 32-byte URL-safe random string. Returned once to the client; only its
    hash is persisted."""
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
