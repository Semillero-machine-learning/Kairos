"""HU-03 — Recuperar la contraseña (RF-07, RN-41, RN-42)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.core.security import hash_opaque_token
from app.modules.auth.models import PasswordResetToken


async def _count_reset_tokens(db, user_id=None) -> int:
    query = select(func.count()).select_from(PasswordResetToken)
    if user_id is not None:
        query = query.where(PasswordResetToken.user_id == user_id)
    return (await db.execute(query)).scalar_one()


@pytest.mark.asyncio
async def test_solicitud_con_correo_registrado(client, make_user, db):
    user = await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")

    response = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "ana@ejemplo.com"}
    )
    assert response.status_code == 202
    assert await _count_reset_tokens(db, user.id) == 1


@pytest.mark.asyncio
async def test_solicitud_con_correo_inexistente(client, make_user, db):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")

    registered = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "ana@ejemplo.com"}
    )
    missing = await client.post(
        "/api/v1/auth/password-reset/request", json={"email": "nadie@ejemplo.com"}
    )

    # Exactamente la misma respuesta, exista o no la cuenta (RN-41).
    assert registered.status_code == missing.status_code == 202
    assert registered.json() == missing.json()
    # No se crea ningún token para el correo inexistente.
    assert await _count_reset_tokens(db) == 1


@pytest.mark.asyncio
async def test_confirmacion_exitosa(client, make_user, db):
    user = await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    login = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "ana@ejemplo.com", "password": "unaClaveLarga123"},
        )
    ).json()

    raw_token = "un-token-de-reset-conocido-123"
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_opaque_token(raw_token),
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
    )
    await db.flush()

    confirm = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "nuevaClaveLarga123"},
    )
    assert confirm.status_code == 204

    # Puede iniciar sesión con la nueva contraseña.
    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "nuevaClaveLarga123"},
    )
    assert ok.status_code == 200

    # Todas las sesiones anteriores quedan revocadas (RN-42).
    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert refreshed.status_code == 401

    # El token no se puede volver a usar.
    reused = await client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": raw_token, "new_password": "otraClaveLarga456"},
    )
    assert reused.status_code == 422
    assert reused.json()["error"]["code"] == "INVALID_RESET_TOKEN"
