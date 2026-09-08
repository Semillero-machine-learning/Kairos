"""La campana: historial, contador de no leídas y marcado (RF-38).

Las notificaciones se generan asignando tareas, que es el camino real: crear
filas a mano probaría la consulta pero no que el evento las produce.
"""

import pytest
import pytest_asyncio

PASSWORD = "unaClaveLarga123"


@pytest_asyncio.fixture
async def con_avisos(make_user, make_project, auth_header, add_member, make_task):
    """Ana termina con dos notificaciones de asignación; Luis con ninguna."""
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    luis = await make_user(email="luis@ejemplo.com", full_name="Luis Pérez")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)

    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)
    await add_member(project["id"], luis.id, "Colaborador", lider)
    await make_task(
        project["id"], lider, title="Limpiar los datos", assignee_ids=(ana.id,)
    )
    await make_task(
        project["id"], lider, title="Entrenar el modelo", assignee_ids=(ana.id,)
    )

    return {
        "project": project,
        "ana": await auth_header("ana@ejemplo.com", PASSWORD),
        "luis": await auth_header("luis@ejemplo.com", PASSWORD),
    }


@pytest.mark.asyncio
async def test_historial_propio(client, con_avisos):
    response = await client.get("/api/v1/notifications", headers=con_avisos["ana"])

    assert response.status_code == 200, response.text
    cuerpo = response.json()
    assert cuerpo["total"] == 2
    assert {item["kind"] for item in cuerpo["items"]} == {"TASK_ASSIGNED"}
    assert all(item["read_at"] is None for item in cuerpo["items"])


@pytest.mark.asyncio
async def test_cada_quien_ve_lo_suyo(client, con_avisos):
    response = await client.get("/api/v1/notifications", headers=con_avisos["luis"])

    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_contador_de_no_leidas(client, con_avisos):
    response = await client.get(
        "/api/v1/notifications/unread-count", headers=con_avisos["ana"]
    )

    assert response.status_code == 200
    assert response.json() == {"unread": 2}


@pytest.mark.asyncio
async def test_marcar_una_como_leida(client, con_avisos):
    listado = await client.get("/api/v1/notifications", headers=con_avisos["ana"])
    primera = listado.json()["items"][0]["id"]

    marcada = await client.post(
        f"/api/v1/notifications/{primera}/read", headers=con_avisos["ana"]
    )

    assert marcada.status_code == 200, marcada.text
    assert marcada.json()["read_at"] is not None
    contador = await client.get(
        "/api/v1/notifications/unread-count", headers=con_avisos["ana"]
    )
    assert contador.json() == {"unread": 1}


@pytest.mark.asyncio
async def test_solo_no_leidas(client, con_avisos):
    listado = await client.get("/api/v1/notifications", headers=con_avisos["ana"])
    primera = listado.json()["items"][0]["id"]
    await client.post(f"/api/v1/notifications/{primera}/read", headers=con_avisos["ana"])

    response = await client.get(
        "/api/v1/notifications?unread_only=true", headers=con_avisos["ana"]
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_marcar_todas_como_leidas(client, con_avisos):
    response = await client.post(
        "/api/v1/notifications/read-all", headers=con_avisos["ana"]
    )

    assert response.status_code == 200, response.text
    assert response.json() == {"marked": 2}
    contador = await client.get(
        "/api/v1/notifications/unread-count", headers=con_avisos["ana"]
    )
    assert contador.json() == {"unread": 0}


@pytest.mark.asyncio
async def test_marcar_todas_dos_veces(client, con_avisos):
    """La segunda no vuelve a tocar nada: las ya leídas conservan su fecha."""
    await client.post("/api/v1/notifications/read-all", headers=con_avisos["ana"])

    segunda = await client.post(
        "/api/v1/notifications/read-all", headers=con_avisos["ana"]
    )

    assert segunda.json() == {"marked": 0}


@pytest.mark.asyncio
async def test_marcar_una_notificacion_ajena(client, con_avisos):
    """404, no 403: un 403 confirmaría que la notificación existe."""
    listado = await client.get("/api/v1/notifications", headers=con_avisos["ana"])
    ajena = listado.json()["items"][0]["id"]

    response = await client.post(
        f"/api/v1/notifications/{ajena}/read", headers=con_avisos["luis"]
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_sin_autenticacion(client):
    response = await client.get("/api/v1/notifications/unread-count")

    assert response.status_code == 401
