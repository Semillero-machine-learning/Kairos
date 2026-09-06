"""HU-02 — Aceptar la invitación (RF-03, RN-38, RN-39, EB-01)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.enums import GlobalRole
from app.modules.auth.models import Invitation


async def _admin_header(client, make_user):
    await make_user(
        email="admin@ejemplo.com", password="unaClaveLarga123", global_role=GlobalRole.ADMIN
    )
    tokens = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@ejemplo.com", "password": "unaClaveLarga123"},
        )
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _invite(client, headers, email="ana@ejemplo.com"):
    response = await client.post(
        "/api/v1/invitations",
        json={"email": email, "global_role": "MEMBER"},
        headers=headers,
    )
    body = response.json()
    token = body["invite_url"].rstrip("/").rsplit("/", 1)[-1]
    return body["id"], token


@pytest.mark.asyncio
async def test_aceptacion_exitosa(client, make_user):
    headers = await _admin_header(client, make_user)
    _, token = await _invite(client, headers)

    # El correo aparece precargado (no editable en el formulario).
    info = await client.get(f"/api/v1/auth/invitations/{token}")
    assert info.status_code == 200
    assert info.json()["email"] == "ana@ejemplo.com"

    accept = await client.post(
        f"/api/v1/auth/invitations/{token}/accept",
        json={"full_name": "Ana Gómez", "password": "claveDeAna12"},
    )
    assert accept.status_code == 200
    body = accept.json()
    assert body["user"]["global_role"] == "MEMBER"
    assert body["user"]["email"] == "ana@ejemplo.com"
    # Queda autenticada automáticamente.
    assert body["access_token"] and body["refresh_token"]

    # El token deja de ser válido tras usarse.
    reused = await client.get(f"/api/v1/auth/invitations/{token}")
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "INVITATION_ALREADY_USED"

    # Puede iniciar sesión con la contraseña recién definida.
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "claveDeAna12"},
    )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_token_vencido(client, make_user, db):
    headers = await _admin_header(client, make_user)
    invitation_id, token = await _invite(client, headers)

    # Simula un enlace emitido hace 8 días.
    invitation = await db.get(Invitation, invitation_id)
    invitation.expires_at = datetime.now(UTC) - timedelta(days=1)
    await db.flush()

    info = await client.get(f"/api/v1/auth/invitations/{token}")
    assert info.status_code == 409
    assert info.json()["error"]["code"] == "INVITATION_EXPIRED"


@pytest.mark.asyncio
async def test_contrasena_demasiado_corta(client, make_user):
    headers = await _admin_header(client, make_user)
    _, token = await _invite(client, headers)

    accept = await client.post(
        f"/api/v1/auth/invitations/{token}/accept",
        json={"full_name": "Ana Gómez", "password": "corta6"},
    )
    assert accept.status_code == 422
    assert accept.json()["error"]["code"] == "VALIDATION_ERROR"

    # La cuenta no se crea: el token sigue disponible.
    still_valid = await client.get(f"/api/v1/auth/invitations/{token}")
    assert still_valid.status_code == 200
