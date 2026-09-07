"""HU-01 — Invitar a un nuevo integrante (RF-01, RF-02, RF-04, EB-02, EB-03)."""

import pytest
from sqlalchemy import select

from app.core.enums import GlobalRole
from app.modules.auth.models import Invitation, InvitationStatus


async def _auth_header(client, email, password):
    tokens = (
        await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_invitacion_exitosa(client, make_user):
    await make_user(
        email="admin@ejemplo.com", password="unaClaveLarga123", global_role=GlobalRole.ADMIN
    )
    headers = await _auth_header(client, "admin@ejemplo.com", "unaClaveLarga123")

    response = await client.post(
        "/api/v1/invitations",
        json={"email": "ana@ejemplo.com", "global_role": "MEMBER"},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["global_role"] == "MEMBER"
    assert body["email"] == "ana@ejemplo.com"
    # The invite URL is returned so the admin can copy it (RF-02).
    assert "/invitacion/" in body["invite_url"]


@pytest.mark.asyncio
async def test_el_correo_ya_tiene_cuenta(client, make_user):
    await make_user(
        email="admin@ejemplo.com", password="unaClaveLarga123", global_role=GlobalRole.ADMIN
    )
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    headers = await _auth_header(client, "admin@ejemplo.com", "unaClaveLarga123")

    response = await client.post(
        "/api/v1/invitations",
        json={"email": "ana@ejemplo.com", "global_role": "MEMBER"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.asyncio
async def test_segunda_invitacion_al_mismo_correo_pendiente(client, make_user, db):
    await make_user(
        email="admin@ejemplo.com", password="unaClaveLarga123", global_role=GlobalRole.ADMIN
    )
    headers = await _auth_header(client, "admin@ejemplo.com", "unaClaveLarga123")

    first = await client.post(
        "/api/v1/invitations",
        json={"email": "ana@ejemplo.com", "global_role": "MEMBER"},
        headers=headers,
    )
    second = await client.post(
        "/api/v1/invitations",
        json={"email": "ana@ejemplo.com", "global_role": "MEMBER"},
        headers=headers,
    )
    assert first.status_code == second.status_code == 201
    assert first.json()["invite_url"] != second.json()["invite_url"]

    rows = (
        (await db.execute(select(Invitation).where(Invitation.email == "ana@ejemplo.com")))
        .scalars()
        .all()
    )
    statuses = sorted(r.status for r in rows)
    # The previous invitation is revoked; exactly one live (PENDING) remains.
    assert statuses == [InvitationStatus.PENDING, InvitationStatus.REVOKED]


@pytest.mark.asyncio
async def test_un_miembro_intenta_invitar(client, make_user):
    await make_user(
        email="miembro@ejemplo.com", password="unaClaveLarga123", global_role=GlobalRole.MEMBER
    )
    headers = await _auth_header(client, "miembro@ejemplo.com", "unaClaveLarga123")

    response = await client.post(
        "/api/v1/invitations",
        json={"email": "nuevo@ejemplo.com", "global_role": "MEMBER"},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
