"""Login, rotating refresh tokens and logout (RF-05, RF-06, RN-43, RN-44)."""

import pytest

from app.core.enums import GlobalRole, UserStatus


@pytest.mark.asyncio
async def test_login_exitoso_devuelve_tokens(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "unaClaveLarga123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == "ana@ejemplo.com"


@pytest.mark.asyncio
async def test_login_credenciales_incorrectas(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "claveIncorrecta"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_login_cuenta_desactivada_mismo_mensaje(client, make_user):
    # A disabled account and a wrong password must yield the same 401 body,
    # so login never reveals which emails exist.
    await make_user(
        email="inactiva@ejemplo.com",
        password="unaClaveLarga123",
        status=UserStatus.DISABLED,
    )
    await make_user(email="activa@ejemplo.com", password="unaClaveLarga123")

    disabled = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactiva@ejemplo.com", "password": "unaClaveLarga123"},
    )
    wrong = await client.post(
        "/api/v1/auth/login",
        json={"email": "activa@ejemplo.com", "password": "claveIncorrecta"},
    )
    assert disabled.status_code == wrong.status_code == 401
    assert disabled.json() == wrong.json()


@pytest.mark.asyncio
async def test_refresh_rota_el_token(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "unaClaveLarga123"},
    )
    old_refresh = login.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["refresh_token"]
    assert new_refresh != old_refresh

    # The old (now revoked) token must no longer work.
    reused = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401


@pytest.mark.asyncio
async def test_reutilizar_token_revocado_revoca_todas_las_sesiones(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "ana@ejemplo.com", "password": "unaClaveLarga123"},
    )
    original = login.json()["refresh_token"]

    rotated = (
        await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    ).json()["refresh_token"]

    # Presenting the revoked original is treated as theft (RN-43): every session
    # is revoked, so even the freshly rotated token stops working.
    reuse = await client.post("/api/v1/auth/refresh", json={"refresh_token": original})
    assert reuse.status_code == 401

    after = await client.post("/api/v1/auth/refresh", json={"refresh_token": rotated})
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_logout_revoca_el_refresco(client, make_user):
    await make_user(email="ana@ejemplo.com", password="unaClaveLarga123")
    login = (
        await client.post(
            "/api/v1/auth/login",
            json={"email": "ana@ejemplo.com", "password": "unaClaveLarga123"},
        )
    ).json()

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": login["refresh_token"]},
        headers={"Authorization": f"Bearer {login['access_token']}"},
    )
    assert logout.status_code == 204

    after = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert after.status_code == 401


@pytest.mark.asyncio
async def test_me_requiere_token(client):
    # No Authorization header: get_current_user rejects with 401.
    response = await client.post("/api/v1/auth/logout", json={"refresh_token": "x"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_puede_iniciar_sesion(client, make_user):
    await make_user(
        email="admin@ejemplo.com",
        password="unaClaveLarga123",
        global_role=GlobalRole.ADMIN,
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ejemplo.com", "password": "unaClaveLarga123"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["global_role"] == "ADMIN"
