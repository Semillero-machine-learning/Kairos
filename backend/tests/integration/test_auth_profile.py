"""Profile and password change (RF-08, RN-42)."""

import pytest


async def _login(client, email, password):
    return (
        await client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
    ).json()


@pytest.mark.asyncio
async def test_me_devuelve_el_perfil(client, make_user):
    await make_user(email="ana@ejemplo.com", full_name="Ana Gómez", password="unaClaveLarga123")
    tokens = await _login(client, "ana@ejemplo.com", "unaClaveLarga123")

    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Ana Gómez"
    assert body["email"] == "ana@ejemplo.com"
    assert body["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_editar_nombre_propio(client, make_user):
    await make_user(email="ana@ejemplo.com", full_name="Ana", password="unaClaveLarga123")
    tokens = await _login(client, "ana@ejemplo.com", "unaClaveLarga123")

    response = await client.patch(
        "/api/v1/auth/me",
        json={"full_name": "Ana Gómez"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Ana Gómez"


@pytest.mark.asyncio
async def test_cambiar_contrasena_con_la_actual(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    tokens = await _login(client, "ana@ejemplo.com", "unaClaveLarga123")

    change = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "unaClaveLarga123", "new_password": "otraClaveLarga456"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert change.status_code == 204

    # New password works; old one no longer does.
    ok = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "otraClaveLarga456"},
    )
    assert ok.status_code == 200
    old = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "unaClaveLarga123"},
    )
    assert old.status_code == 401


@pytest.mark.asyncio
async def test_cambiar_contrasena_revoca_sesiones(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    tokens = await _login(client, "ana@ejemplo.com", "unaClaveLarga123")

    await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "unaClaveLarga123", "new_password": "otraClaveLarga456"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    # RN-42: the refresh token issued before the change is revoked.
    refreshed = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refreshed.status_code == 401


@pytest.mark.asyncio
async def test_cambiar_contrasena_actual_incorrecta(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    tokens = await _login(client, "ana@ejemplo.com", "unaClaveLarga123")

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "equivocada", "new_password": "otraClaveLarga456"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cambiar_contrasena_demasiado_corta(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    tokens = await _login(client, "ana@ejemplo.com", "unaClaveLarga123")

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "unaClaveLarga123", "new_password": "corta"},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
