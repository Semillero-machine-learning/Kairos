"""Unit tests for password hashing and JWT issuing."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.enums import GlobalRole
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_opaque_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("unaClaveLarga123")
    assert hashed != "unaClaveLarga123"
    assert verify_password("unaClaveLarga123", hashed) is True


def test_password_wrong_is_rejected():
    hashed = hash_password("unaClaveLarga123")
    assert verify_password("otraClave", hashed) is False


def test_password_hash_uses_argon2id():
    assert hash_password("x" * 12).startswith("$argon2id$")


def test_access_token_carries_role_but_no_permissions():
    user_id = uuid.uuid4()
    token = create_access_token(user_id, GlobalRole.ADMIN)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["global_role"] == "ADMIN"
    assert "jti" in payload
    # RN-22: permissions must never travel inside the token.
    assert "permissions" not in payload
    assert "project_permissions" not in payload


def test_expired_access_token_raises():
    settings = get_settings()
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "global_role": "MEMBER",
            "iat": int((datetime.now(UTC) - timedelta(hours=2)).timestamp()),
            "exp": int((datetime.now(UTC) - timedelta(hours=1)).timestamp()),
            "jti": uuid.uuid4().hex,
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        decode_access_token(expired)


def test_tampered_access_token_raises():
    with pytest.raises(AuthenticationError):
        decode_access_token("not-a-real-token")


def test_opaque_token_hash_is_deterministic_and_tokens_unique():
    token = generate_opaque_token()
    assert hash_opaque_token(token) == hash_opaque_token(token)
    assert generate_opaque_token() != generate_opaque_token()
    assert token not in hash_opaque_token(token)
