"""Administración de usuarios y roles globales (RF-09, RF-10, RF-11, RF-12, RN-02, EB-11)."""

import pytest

from app.core.enums import GlobalRole, UserStatus


async def _header(client, email, password="unaClaveLarga123"):
    tokens = (
        await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_admin_lista_usuarios_con_todos_los_campos(client, make_user):
    await make_user(email="admin@ejemplo.com", global_role=GlobalRole.ADMIN)
    await make_user(email="ana@ejemplo.com")
    headers = await _header(client, "admin@ejemplo.com")

    response = await client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert all(item["global_role"] is not None for item in body["items"])


@pytest.mark.asyncio
async def test_miembro_ve_version_reducida_solo_activos(client, make_user):
    await make_user(email="miembro@ejemplo.com", global_role=GlobalRole.MEMBER)
    await make_user(email="ana@ejemplo.com")
    await make_user(email="inactiva@ejemplo.com", status=UserStatus.DISABLED)
    headers = await _header(client, "miembro@ejemplo.com")

    response = await client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200
    body = response.json()
    # Solo usuarios activos (miembro + ana), sin campos de administración.
    emails = {item["email"] for item in body["items"]}
    assert "inactiva@ejemplo.com" not in emails
    assert all(item["global_role"] is None for item in body["items"])
    assert all(item["status"] is None for item in body["items"])


@pytest.mark.asyncio
async def test_buscar_por_correo(client, make_user):
    await make_user(email="admin@ejemplo.com", global_role=GlobalRole.ADMIN)
    await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    await make_user(email="luis@ejemplo.com", full_name="Luis Pérez")
    headers = await _header(client, "admin@ejemplo.com")

    response = await client.get("/api/v1/users?search=luis", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "luis@ejemplo.com"


@pytest.mark.asyncio
async def test_cambiar_rol_global(client, make_user):
    await make_user(email="admin@ejemplo.com", global_role=GlobalRole.ADMIN)
    ana = await make_user(email="ana@ejemplo.com", global_role=GlobalRole.MEMBER)
    headers = await _header(client, "admin@ejemplo.com")

    response = await client.patch(
        f"/api/v1/users/{ana.id}/role",
        json={"global_role": "LESSON_EDITOR"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["global_role"] == "LESSON_EDITOR"


@pytest.mark.asyncio
async def test_ultimo_admin_no_puede_degradarse(client, make_user):
    admin = await make_user(email="admin@ejemplo.com", global_role=GlobalRole.ADMIN)
    headers = await _header(client, "admin@ejemplo.com")

    response = await client.patch(
        f"/api/v1/users/{admin.id}/role",
        json={"global_role": "MEMBER"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_ADMIN"


@pytest.mark.asyncio
async def test_ultimo_admin_no_puede_desactivarse(client, make_user):
    admin = await make_user(email="admin@ejemplo.com", global_role=GlobalRole.ADMIN)
    headers = await _header(client, "admin@ejemplo.com")

    response = await client.patch(
        f"/api/v1/users/{admin.id}/status",
        json={"status": "DISABLED"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_ADMIN"


@pytest.mark.asyncio
async def test_con_dos_admins_uno_puede_degradarse(client, make_user):
    await make_user(email="admin1@ejemplo.com", global_role=GlobalRole.ADMIN)
    admin2 = await make_user(email="admin2@ejemplo.com", global_role=GlobalRole.ADMIN)
    headers = await _header(client, "admin1@ejemplo.com")

    response = await client.patch(
        f"/api/v1/users/{admin2.id}/role",
        json={"global_role": "MEMBER"},
        headers=headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_desactivar_usuario_le_impide_iniciar_sesion(client, make_user):
    await make_user(email="admin@ejemplo.com", global_role=GlobalRole.ADMIN)
    ana = await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    headers = await _header(client, "admin@ejemplo.com")

    disable = await client.patch(
        f"/api/v1/users/{ana.id}/status", json={"status": "DISABLED"}, headers=headers
    )
    assert disable.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "unaClaveLarga123"},
    )
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_miembro_no_puede_administrar(client, make_user):
    await make_user(email="miembro@ejemplo.com", global_role=GlobalRole.MEMBER)
    otro = await make_user(email="otro@ejemplo.com")
    headers = await _header(client, "miembro@ejemplo.com")

    detail = await client.get(f"/api/v1/users/{otro.id}", headers=headers)
    assert detail.status_code == 403

    role = await client.patch(
        f"/api/v1/users/{otro.id}/role", json={"global_role": "ADMIN"}, headers=headers
    )
    assert role.status_code == 403
