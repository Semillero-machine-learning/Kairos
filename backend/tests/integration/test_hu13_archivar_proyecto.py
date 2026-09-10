"""HU-13 — Archivar un proyecto terminado (RF-18, RN-15, RN-16, EB-06).

Scenario names mirror docs/user-stories.md.

The archived guard itself is exercised in
``test_project_permission_dependency.py``; this file is the traceable version of
the story, and it goes one step further on the last scenario: RN-16 says
archiving stops every notification, so unarchiving has to bring the reminders
back. That is asserted against the job, not against the project's status.
"""

import datetime

import pytest
import pytest_asyncio

from app.jobs.reminders import run_reminders

PASSWORD = "unaClaveLarga123"
# A fixed day, so the test does not depend on when it runs.
HOY = datetime.date(2026, 6, 15)


@pytest_asyncio.fixture
async def proyecto_terminado(
    client, make_user, make_project, auth_header, add_member, get_roles, make_task
):
    """Un proyecto con su líder, un colaborador, una tarea y una entrega.

    Se archiva un proyecto que tuvo vida, no uno vacío: el escenario dice que
    después de archivarlo se sigue consultando «con todas sus tareas y
    entregas», y sin ellas esa parte no probaría nada.
    """
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    luis = await make_user(email="luis@ejemplo.com", full_name="Luis Pérez")
    project = await make_project(name="Detección de anomalías", leader_id=ana.id)

    lider = await auth_header("ana@ejemplo.com", PASSWORD)
    colaborador = await auth_header("luis@ejemplo.com", PASSWORD)
    await add_member(project["id"], luis.id, "Colaborador", lider)

    task = await make_task(
        project["id"],
        lider,
        title="Entrenar el modelo base",
        due_date=(HOY + datetime.timedelta(days=1)).isoformat(),
        assignee_ids=(str(luis.id),),
    )

    # La tarea nace en BACKLOG y entregar la empuja a revisión, que no es
    # transición válida desde ahí: primero se pone en marcha.
    for estado in ("TODO", "IN_PROGRESS"):
        avance = await client.post(
            f"/api/v1/tasks/{task['id']}/status", json={"status": estado}, headers=lider
        )
        assert avance.status_code == 200, avance.text

    # La entrega la registra el responsable, que es quien puede (RN).
    entrega = await client.post(
        f"/api/v1/tasks/{task['id']}/submissions",
        json={
            "description": "Cuaderno con la línea base y sus métricas.",
            "commit_url": "https://github.com/semillero/anomalias/commit/9f2a1c4",
        },
        headers=colaborador,
    )
    assert entrega.status_code == 201, entrega.text

    roles = await get_roles(project["id"], lider)

    return {
        "project": project,
        "task": task,
        "ana": ana,
        "luis": luis,
        "lider": lider,
        "colaborador": colaborador,
        "observador_role_id": roles["Observador"]["id"],
    }


@pytest.mark.asyncio
async def test_archivado(client, proyecto_terminado):
    project = proyecto_terminado["project"]
    lider = proyecto_terminado["lider"]
    task = proyecto_terminado["task"]

    # Dado que tengo el permiso "project.archive"
    detalle = await client.get(f"/api/v1/projects/{project['id']}", headers=lider)
    assert "project.archive" in detalle.json()["my_permissions"]

    # Cuando archivo el proyecto
    response = await client.post(f"/api/v1/projects/{project['id']}/archive", headers=lider)

    # Entonces queda en estado "ARCHIVED" con su fecha de archivado
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ARCHIVED"
    assert response.json()["archived_at"] is not None

    # Y desaparece de la lista de proyectos activos
    activos = await client.get("/api/v1/projects", params={"status": "ACTIVE"}, headers=lider)
    assert project["id"] not in [p["id"] for p in activos.json()["items"]]

    # Y sigue siendo consultable con todas sus tareas y entregas
    consultado = await client.get(f"/api/v1/projects/{project['id']}", headers=lider)
    assert consultado.status_code == 200
    assert consultado.json()["name"] == project["name"]

    tareas = await client.get(f"/api/v1/projects/{project['id']}/tasks", headers=lider)
    assert tareas.status_code == 200
    assert [t["id"] for t in tareas.json()["items"]] == [task["id"]]

    entregas = await client.get(f"/api/v1/tasks/{task['id']}/submissions", headers=lider)
    assert entregas.status_code == 200
    assert len(entregas.json()) == 1


@pytest.mark.asyncio
async def test_escritura_sobre_proyecto_archivado(client, proyecto_terminado):
    project = proyecto_terminado["project"]
    lider = proyecto_terminado["lider"]
    task = proyecto_terminado["task"]
    luis = proyecto_terminado["luis"]

    # Dado que el proyecto está archivado
    archivado = await client.post(f"/api/v1/projects/{project['id']}/archive", headers=lider)
    assert archivado.status_code == 200

    # Cuando intento crear una tarea, comentar o agregar un miembro
    intentos = {
        "crear una tarea": await client.post(
            f"/api/v1/projects/{project['id']}/tasks",
            json={"title": "Otra tarea más"},
            headers=lider,
        ),
        "comentar": await client.post(
            f"/api/v1/tasks/{task['id']}/comments",
            json={"body": "Un comentario que no debería entrar."},
            headers=lider,
        ),
        "agregar un miembro": await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={
                "user_id": str(luis.id),
                "project_role_id": proyecto_terminado["observador_role_id"],
            },
            headers=lider,
        ),
    }

    # Entonces cada intento devuelve un error 409 con el código "PROJECT_ARCHIVED"
    for intento, response in intentos.items():
        assert response.status_code == 409, f"{intento}: {response.status_code} {response.text}"
        assert response.json()["error"]["code"] == "PROJECT_ARCHIVED", intento


@pytest.mark.asyncio
async def test_desarchivado(client, db, proyecto_terminado):
    project = proyecto_terminado["project"]
    lider = proyecto_terminado["lider"]

    await client.post(f"/api/v1/projects/{project['id']}/archive", headers=lider)

    # Mientras está archivado no se recuerda nada suyo (RN-16). Se comprueba
    # antes de desarchivar para que la reanudación signifique algo: la tarea
    # vence mañana, así que sin el archivado habría aviso.
    callado = await run_reminders(db, today=HOY)
    assert callado.due_soon_sent == 0

    # Cuando desarchivo el proyecto
    response = await client.post(f"/api/v1/projects/{project['id']}/unarchive", headers=lider)

    # Entonces vuelve a estado "ACTIVE"
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ACTIVE"
    assert response.json()["archived_at"] is None

    # Y las notificaciones se reanudan
    reanudado = await run_reminders(db, today=HOY)
    assert reanudado.due_soon_sent == 1
