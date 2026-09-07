"""HU-07 — Crear y asignar una tarea (RF-25, RF-26, RF-27).

Scenario names mirror docs/user-stories.md so a failure points straight at the
acceptance criterion it broke.
"""

import datetime

import pytest

from app.core.clock import today_in_bogota

PASSWORD = "unaClaveLarga123"


@pytest.fixture
def hoy() -> datetime.date:
    """Today as the server sees it: a calendar day in Bogotá, not in UTC."""
    return today_in_bogota()


@pytest.mark.asyncio
async def test_creacion_con_dos_responsables(
    client, make_user, make_project, auth_header, add_member
):
    # Dado que soy líder del proyecto
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    luis = await make_user(email="luis@ejemplo.com", full_name="Luis Pérez")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)
    await add_member(project["id"], luis.id, "Colaborador", lider)

    # Cuando creo la tarea "Entrenar el modelo base" con periodicidad "WEEKLY",
    # fecha límite "2026-09-20" y responsables "Ana" y "Luis"
    response = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={
            "title": "Entrenar el modelo base",
            "description": "Con los datos de agosto.",
            "periodicity": "WEEKLY",
            "due_date": "2026-09-20",
            "assignee_ids": [str(ana.id), str(luis.id)],
        },
        headers=lider,
    )

    assert response.status_code == 201, response.text
    task = response.json()
    # Entonces la tarea queda en estado "BACKLOG"
    assert task["status"] == "BACKLOG"
    assert task["periodicity"] == "WEEKLY"
    assert task["due_date"] == "2026-09-20"
    assert task["completed_at"] is None
    assert task["created_by"]["full_name"] == "Carlos"
    assert {a["full_name"] for a in task["assignees"]} == {"Ana Gómez", "Luis Pérez"}

    # Y "Ana" y "Luis" reciben una notificación en la aplicación
    # Y ambos reciben un correo con el título, el proyecto y la fecha límite
    #
    # Las dos últimas líneas del escenario son RF-39, que el roadmap sitúa en la
    # Fase 5 junto con la tabla `notifications`. Se verifican aquí cuando ese
    # módulo exista; la tarea y sus responsables, que son lo que la Fase 3
    # promete, ya quedan comprobados arriba.


@pytest.mark.asyncio
async def test_la_periodicidad_no_genera_tareas(
    client, make_user, make_project, auth_header, make_task, hoy
):
    # Dado que existe una tarea con periodicidad "WEEKLY" y fecha límite de la
    # semana pasada
    carlos = await make_user(email="carlos@ejemplo.com")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await make_task(
        project["id"],
        lider,
        title="Reporte semanal",
        periodicity="WEEKLY",
        due_date=str(hoy - datetime.timedelta(days=7)),
    )

    # Cuando pasa una semana (el sistema no tiene ningún proceso que lo haga:
    # la periodicidad es una etiqueta, RF-26)
    response = await client.get(f"/api/v1/projects/{project['id']}/tasks", headers=lider)

    # Entonces no se crea ninguna tarea nueva automáticamente
    assert response.status_code == 200, response.text
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_fecha_limite_en_el_pasado(
    client, make_user, make_project, auth_header, hoy
):
    carlos = await make_user(email="carlos@ejemplo.com")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)

    # Cuando creo una tarea con fecha límite anterior a hoy
    response = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={
            "title": "Tarea registrada tarde",
            "due_date": str(hoy - datetime.timedelta(days=1)),
        },
        headers=lider,
    )

    # Entonces la tarea se crea
    assert response.status_code == 201, response.text
    # Y la interfaz muestra una advertencia visible: el backend le da el dato con
    # el que pintarla, calculado contra la fecha de Bogotá y no almacenado.
    assert response.json()["is_overdue"] is True


@pytest.mark.asyncio
async def test_sin_el_permiso_de_crear_no_se_crea(
    client, make_user, make_project, auth_header, add_member
):
    carlos = await make_user(email="carlos@ejemplo.com")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)

    response = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Una tarea cualquiera"},
        headers=await auth_header("ana@ejemplo.com", PASSWORD),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_no_se_asigna_a_quien_no_es_miembro(
    client, make_user, make_project, auth_header
):
    # Un responsable ajeno al proyecto no podría ni ver la tarea que le tocaría.
    carlos = await make_user(email="carlos@ejemplo.com")
    ajena = await make_user(email="ajena@ejemplo.com", full_name="Persona Ajena")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)

    response = await client.post(
        f"/api/v1/projects/{project['id']}/tasks",
        json={"title": "Entrenar el modelo", "assignee_ids": [str(ajena.id)]},
        headers=lider,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_se_agrega_y_se_quita_un_responsable(
    client, make_user, make_project, auth_header, add_member, make_task
):
    carlos = await make_user(email="carlos@ejemplo.com")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)
    task = await make_task(project["id"], lider)

    added = await client.post(
        f"/api/v1/tasks/{task['id']}/assignees",
        json={"user_id": str(ana.id)},
        headers=lider,
    )
    assert added.status_code == 200, added.text
    assert [a["full_name"] for a in added.json()["assignees"]] == ["Ana"]

    # Repetir la asignación no duplica la fila.
    repeated = await client.post(
        f"/api/v1/tasks/{task['id']}/assignees",
        json={"user_id": str(ana.id)},
        headers=lider,
    )
    assert repeated.status_code == 409

    # La tarea sobrevive sin responsables: el tablero la muestra sin asignar
    # (EB-04).
    removed = await client.delete(
        f"/api/v1/tasks/{task['id']}/assignees/{ana.id}", headers=lider
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["assignees"] == []
