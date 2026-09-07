"""HU-08 — Trabajar y entregar (RF-30, RF-31, RF-32, RN-10).

Scenario names mirror docs/user-stories.md so a failure points straight at the
acceptance criterion it broke.
"""

import pytest
import pytest_asyncio

PASSWORD = "unaClaveLarga123"
COMMIT_URL = "https://github.com/semillero-ml/anomalias/commit/a1b2c3d"
ENTREGA = (
    "Entrené el modelo base con los datos de agosto. Exactitud del 0.87 en validación."
)


@pytest_asyncio.fixture
async def escenario(make_user, make_project, auth_header, add_member, make_task, move_task):
    """Un proyecto con una tarea en "TODO" asignada a Ana.

    Ana y Luis son Colaboradores: su rol solo tiene "task.view" y "task.comment",
    que es justo la precondición de los dos primeros escenarios.
    """
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    luis = await make_user(email="luis@ejemplo.com", full_name="Luis Pérez")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)

    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)
    await add_member(project["id"], luis.id, "Colaborador", lider)

    task = await make_task(project["id"], lider, assignee_ids=(ana.id,))
    passed = await move_task(task["id"], "TODO", lider)
    assert passed.status_code == 200, passed.text

    return {
        "project": project,
        "task": task,
        "lider": lider,
        "ana": await auth_header("ana@ejemplo.com", PASSWORD),
        "luis": await auth_header("luis@ejemplo.com", PASSWORD),
    }


@pytest_asyncio.fixture
async def en_progreso(escenario, move_task):
    """El mismo escenario, con la tarea ya movida a "IN_PROGRESS" por Ana."""
    response = await move_task(escenario["task"]["id"], "IN_PROGRESS", escenario["ana"])
    assert response.status_code == 200, response.text
    return escenario


@pytest.mark.asyncio
async def test_mover_la_tarea_propia_sin_permisos_especiales(escenario, move_task):
    # Dado que soy responsable de una tarea en estado "TODO"
    # Y mi rol solo tiene "task.view" y "task.comment"
    # Cuando muevo la tarea a "IN_PROGRESS"
    response = await move_task(escenario["task"]["id"], "IN_PROGRESS", escenario["ana"])

    # Entonces la operación tiene éxito
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_mover_una_tarea_ajena(escenario, move_task):
    # Dado que no soy responsable de la tarea
    # Y mi rol no tiene "task.change_status_any"
    # Cuando intento moverla a "IN_PROGRESS"
    response = await move_task(escenario["task"]["id"], "IN_PROGRESS", escenario["luis"])

    # Entonces recibo un error 403
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_entrega_exitosa(client, en_progreso):
    # Dado que soy responsable de una tarea en estado "IN_PROGRESS"
    task_id = en_progreso["task"]["id"]

    # Cuando registro una entrega con la descripción de lo realizado y la URL
    response = await client.post(
        f"/api/v1/tasks/{task_id}/submissions",
        json={"description": ENTREGA, "commit_url": COMMIT_URL},
        headers=en_progreso["ana"],
    )

    assert response.status_code == 201, response.text
    # Y la entrega queda en estado "PENDING"
    submission = response.json()
    assert submission["review_status"] == "PENDING"
    assert submission["commit_url"] == COMMIT_URL
    assert submission["submitted_by"]["full_name"] == "Ana Gómez"
    assert submission["reviewed_at"] is None

    # Entonces la tarea pasa a "IN_REVIEW"
    task = await client.get(f"/api/v1/tasks/{task_id}", headers=en_progreso["ana"])
    assert task.json()["status"] == "IN_REVIEW"


@pytest.mark.asyncio
async def test_pasar_a_revision_sin_entrega(en_progreso, move_task):
    # Cuando intento mover la tarea a "IN_REVIEW" sin registrar entrega
    response = await move_task(
        en_progreso["task"]["id"], "IN_REVIEW", en_progreso["ana"]
    )

    # Entonces recibo un error 409 con el código "SUBMISSION_REQUIRED"
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBMISSION_REQUIRED"


@pytest.mark.asyncio
async def test_url_que_no_es_de_github(client, en_progreso):
    # Cuando registro una entrega con la URL "https://drive.google.com/archivo"
    response = await client.post(
        f"/api/v1/tasks/{en_progreso['task']['id']}/submissions",
        json={"description": ENTREGA, "commit_url": "https://drive.google.com/archivo"},
        headers=en_progreso["ana"],
    )

    # Entonces recibo un error de validación indicando el formato esperado
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_ERROR"
    assert "github.com" in str(body["details"])


@pytest.mark.asyncio
async def test_segunda_entrega_mientras_hay_una_pendiente(client, en_progreso):
    task_id = en_progreso["task"]["id"]
    # Dado que la tarea ya tiene una entrega en estado "PENDING"
    first = await client.post(
        f"/api/v1/tasks/{task_id}/submissions",
        json={"description": ENTREGA},
        headers=en_progreso["ana"],
    )
    assert first.status_code == 201, first.text

    # Cuando intento registrar otra
    response = await client.post(
        f"/api/v1/tasks/{task_id}/submissions",
        json={"description": "Un segundo intento con más detalle del trabajo."},
        headers=en_progreso["ana"],
    )

    # Entonces recibo un error 409 con el código "SUBMISSION_ALREADY_PENDING"
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBMISSION_ALREADY_PENDING"


@pytest.mark.asyncio
async def test_transicion_no_permitida(escenario, move_task):
    # Dado que la tarea está en "TODO"
    # Cuando intento moverla directamente a "DONE"
    response = await move_task(escenario["task"]["id"], "DONE", escenario["lider"])

    # Entonces recibo un error 409 con el código "INVALID_TRANSITION"
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INVALID_TRANSITION"
    # Y el mensaje enumera las transiciones válidas desde "TODO"
    assert "IN_PROGRESS" in error["message"] and "BACKLOG" in error["message"]
    assert error["details"]["allowed"] == ["IN_PROGRESS", "BACKLOG"]


@pytest.mark.asyncio
async def test_solo_un_responsable_registra_la_entrega(client, en_progreso):
    # El líder tiene los 14 permisos y aun así no entrega por otro: entregar es
    # una regla de propiedad, no un permiso del catálogo.
    response = await client.post(
        f"/api/v1/tasks/{en_progreso['task']['id']}/submissions",
        json={"description": ENTREGA},
        headers=en_progreso["lider"],
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_ASSIGNEE"


@pytest.mark.asyncio
async def test_la_revision_no_pasa_por_el_cambio_de_estado(client, en_progreso, move_task):
    # Una tarea en revisión no sale de ahí cambiando el estado a mano: aprobar
    # marca la entrega y devolver exige comentario (RN-07, RN-09).
    task_id = en_progreso["task"]["id"]
    entregada = await client.post(
        f"/api/v1/tasks/{task_id}/submissions",
        json={"description": ENTREGA},
        headers=en_progreso["ana"],
    )
    assert entregada.status_code == 201, entregada.text

    response = await move_task(task_id, "DONE", en_progreso["lider"])

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"


@pytest.mark.asyncio
async def test_el_historial_conserva_todas_las_entregas(client, en_progreso):
    # RF-34: la tarea guarda todo su historial, no solo la última entrega.
    task_id = en_progreso["task"]["id"]
    await client.post(
        f"/api/v1/tasks/{task_id}/submissions",
        json={"description": ENTREGA, "commit_url": COMMIT_URL},
        headers=en_progreso["ana"],
    )

    response = await client.get(
        f"/api/v1/tasks/{task_id}/submissions", headers=en_progreso["luis"]
    )

    assert response.status_code == 200, response.text
    historial = response.json()
    assert len(historial) == 1
    assert historial[0]["description"] == ENTREGA
