"""«Mis tareas» entre todos los proyectos (RF-36).

La vista personal del panel de inicio: cruza los proyectos del usuario y solo
muestra lo que es suyo.
"""

import datetime

import pytest
import pytest_asyncio

from app.core.clock import today_in_bogota

PASSWORD = "unaClaveLarga123"


@pytest_asyncio.fixture
async def dos_proyectos(make_user, make_project, auth_header, add_member, make_task):
    """Ana es Colaboradora en dos proyectos y tiene una tarea en cada uno."""
    hoy = today_in_bogota()
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana")
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)

    anomalias = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    vision = await make_project(name="Visión por computador", leader_id=carlos.id)
    await add_member(anomalias["id"], ana.id, "Colaborador", lider)
    await add_member(vision["id"], ana.id, "Colaborador", lider)

    await make_task(
        anomalias["id"],
        lider,
        title="Entrenar el modelo base",
        due_date=str(hoy + datetime.timedelta(days=3)),
        assignee_ids=(ana.id,),
    )
    await make_task(
        vision["id"],
        lider,
        title="Etiquetar el conjunto de imágenes",
        due_date=str(hoy + datetime.timedelta(days=1)),
        assignee_ids=(ana.id,),
    )
    # De nadie: no debe aparecer en la lista de Ana.
    await make_task(anomalias["id"], lider, title="Tarea sin responsables")

    return {
        "anomalias": anomalias,
        "vision": vision,
        "ana_id": ana.id,
        "ana": await auth_header("ana@ejemplo.com", PASSWORD),
        "lider": lider,
        "hoy": hoy,
    }


@pytest.mark.asyncio
async def test_cruza_todos_los_proyectos_del_usuario(client, dos_proyectos):
    response = await client.get("/api/v1/me/tasks", headers=dos_proyectos["ana"])

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    # Ordenadas por fecha límite, la más próxima primero.
    assert [task["title"] for task in body["items"]] == [
        "Etiquetar el conjunto de imágenes",
        "Entrenar el modelo base",
    ]
    # Cada tarea trae el nombre de su proyecto, para el panel de inicio.
    assert [task["project"]["name"] for task in body["items"]] == [
        "Visión por computador",
        "Detección de anomalías",
    ]


@pytest.mark.asyncio
async def test_filtra_por_estado_y_por_fecha(client, dos_proyectos, move_task):
    listed = await client.get("/api/v1/me/tasks", headers=dos_proyectos["ana"])
    etiquetar = next(
        task
        for task in listed.json()["items"]
        if task["title"] == "Etiquetar el conjunto de imágenes"
    )
    await move_task(etiquetar["id"], "TODO", dos_proyectos["lider"])

    por_estado = await client.get(
        "/api/v1/me/tasks?status=TODO", headers=dos_proyectos["ana"]
    )
    assert [t["title"] for t in por_estado.json()["items"]] == [
        "Etiquetar el conjunto de imágenes"
    ]

    limite = dos_proyectos["hoy"] + datetime.timedelta(days=1)
    por_fecha = await client.get(
        f"/api/v1/me/tasks?due_before={limite}", headers=dos_proyectos["ana"]
    )
    assert [t["title"] for t in por_fecha.json()["items"]] == [
        "Etiquetar el conjunto de imágenes"
    ]


@pytest.mark.asyncio
async def test_no_muestra_las_tareas_de_un_proyecto_del_que_ya_no_es_miembro(
    client, dos_proyectos
):
    # RF-16: retirar a alguien no borra sus tareas, pero deja de verlas.
    removed = await client.delete(
        f"/api/v1/projects/{dos_proyectos['vision']['id']}/members/{dos_proyectos['ana_id']}",
        headers=dos_proyectos["lider"],
    )
    assert removed.status_code == 204, removed.text

    response = await client.get("/api/v1/me/tasks", headers=dos_proyectos["ana"])

    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Entrenar el modelo base"

    # Y la tarea sigue existiendo, con su responsable intacto, para el proyecto.
    tablero = await client.get(
        f"/api/v1/projects/{dos_proyectos['vision']['id']}/tasks",
        headers=dos_proyectos["lider"],
    )
    etiquetar = tablero.json()["items"][0]
    assert etiquetar["title"] == "Etiquetar el conjunto de imágenes"
    assert [a["full_name"] for a in etiquetar["assignees"]] == ["Ana"]


@pytest.mark.asyncio
async def test_quien_no_tiene_tareas_recibe_una_lista_vacia(client, make_user, auth_header):
    await make_user(email="sola@ejemplo.com", full_name="Persona Sola")

    response = await client.get(
        "/api/v1/me/tasks", headers=await auth_header("sola@ejemplo.com", PASSWORD)
    )

    assert response.status_code == 200
    assert response.json() == {"items": [], "total": 0, "page": 1, "size": 20}
