"""HU-09 — Revisar una entrega (RF-33, RF-34, RN-07, RN-09, RN-12).

Scenario names mirror docs/user-stories.md so a failure points straight at the
acceptance criterion it broke. The notification half of the two review scenarios
lives in test_notifications_events.py, where the inbox is available to assert on.
"""

import pytest
import pytest_asyncio

PASSWORD = "unaClaveLarga123"
COMMIT_URL = "https://github.com/semillero-ml/anomalias/commit/a1b2c3d"
ENTREGA = (
    "Entrené el modelo base con los datos de agosto. Exactitud del 0.87 en validación."
)
SEGUNDA_ENTREGA = "Agregué la evaluación en el conjunto de prueba, con matriz de confusión."
DEVOLUCION = "Falta la evaluación en prueba"


@pytest_asyncio.fixture
async def en_revision(
    client, make_user, make_project, auth_header, add_member, make_task, move_task
):
    """Una tarea en "IN_REVIEW" con una entrega pendiente de Ana.

    Carlos es el líder, así que tiene "task.review" y no es responsable: es el
    segundo par de ojos que RN-07 exige. Ana es Colaboradora, de modo que solo
    llega a tener "task.review" en el escenario de autoaprobación, que se lo da
    a propósito.
    """
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)

    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)

    task = await make_task(project["id"], lider, assignee_ids=(ana.id,))
    ana_headers = await auth_header("ana@ejemplo.com", PASSWORD)
    assert (await move_task(task["id"], "TODO", lider)).status_code == 200
    assert (await move_task(task["id"], "IN_PROGRESS", ana_headers)).status_code == 200

    response = await client.post(
        f"/api/v1/tasks/{task['id']}/submissions",
        json={"description": ENTREGA, "commit_url": COMMIT_URL},
        headers=ana_headers,
    )
    assert response.status_code == 201, response.text

    return {
        "project": project,
        "task": task,
        "submission": response.json(),
        "lider": lider,
        "ana": ana_headers,
        "ana_user": ana,
        "carlos_user": carlos,
    }


@pytest.mark.asyncio
async def test_aprobacion(client, en_revision):
    # Dado que tengo el permiso "task.review"
    # Y no soy responsable de la tarea
    # Y la tarea está en "IN_REVIEW" con una entrega pendiente
    # Cuando apruebo la entrega
    response = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": True},
        headers=en_revision["lider"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["review_status"] == "APPROVED"
    assert body["reviewed_by"]["email"] == "carlos@ejemplo.com"
    assert body["reviewed_at"] is not None

    # Entonces la tarea pasa a "DONE"
    task = await client.get(
        f"/api/v1/tasks/{en_revision['task']['id']}", headers=en_revision["lider"]
    )
    assert task.json()["status"] == "DONE"
    # Y se registra la fecha de finalización
    assert task.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_devolucion(client, en_revision):
    # Cuando devuelvo la entrega con el comentario "Falta la evaluación en prueba"
    response = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": False, "comment": DEVOLUCION},
        headers=en_revision["lider"],
    )

    assert response.status_code == 200, response.text
    body = response.json()
    # Y la entrega queda en estado "REJECTED" conservando el comentario
    assert body["review_status"] == "REJECTED"
    assert body["review_comment"] == DEVOLUCION

    # Entonces la tarea vuelve a "IN_PROGRESS"
    task = await client.get(
        f"/api/v1/tasks/{en_revision['task']['id']}", headers=en_revision["lider"]
    )
    assert task.json()["status"] == "IN_PROGRESS"
    assert task.json()["completed_at"] is None


@pytest.mark.asyncio
async def test_devolucion_sin_comentario(client, en_revision):
    # Cuando devuelvo la entrega sin comentario
    response = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": False},
        headers=en_revision["lider"],
    )

    # Entonces recibo un error 422 con el código "REVIEW_COMMENT_REQUIRED"
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REVIEW_COMMENT_REQUIRED"


@pytest.mark.asyncio
async def test_devolucion_con_comentario_en_blanco(client, en_revision):
    """Un campo de texto vacío llega como cadena vacía desde un formulario:
    cuenta como ausente, no como explicación (RN-09)."""
    response = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": False, "comment": "   "},
        headers=en_revision["lider"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "REVIEW_COMMENT_REQUIRED"


@pytest.mark.asyncio
async def test_autoaprobacion(client, en_revision, get_roles):
    # Dado que tengo el permiso "task.review"
    roles = await get_roles(en_revision["project"]["id"], en_revision["lider"])
    project_id = en_revision["project"]["id"]
    ana_id = en_revision["ana_user"].id
    cambio = await client.patch(
        f"/api/v1/projects/{project_id}/members/{ana_id}/role",
        json={"project_role_id": roles["Líder"]["id"]},
        headers=en_revision["lider"],
    )
    assert cambio.status_code == 200, cambio.text

    # Y soy responsable de la tarea
    # Cuando intento aprobar mi propia entrega
    response = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": True},
        headers=en_revision["ana"],
    )

    # Entonces recibo un error 403 con el código "CANNOT_REVIEW_OWN_SUBMISSION"
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CANNOT_REVIEW_OWN_SUBMISSION"


@pytest.mark.asyncio
async def test_autodevolucion(client, en_revision, get_roles):
    """La otra salida de IN_REVIEW se cierra igual: si un responsable pudiera
    devolverse su propia entrega, el segundo par de ojos de RN-07 sería opcional.
    """
    roles = await get_roles(en_revision["project"]["id"], en_revision["lider"])
    project_id = en_revision["project"]["id"]
    ana_id = en_revision["ana_user"].id
    cambio = await client.patch(
        f"/api/v1/projects/{project_id}/members/{ana_id}/role",
        json={"project_role_id": roles["Líder"]["id"]},
        headers=en_revision["lider"],
    )
    assert cambio.status_code == 200, cambio.text

    response = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": False, "comment": DEVOLUCION},
        headers=en_revision["ana"],
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CANNOT_REVIEW_OWN_SUBMISSION"


@pytest.mark.asyncio
async def test_sin_permiso_de_revision(client, en_revision):
    """Ana es Colaboradora: su rol no tiene "task.review" (RN-07, primera frase)."""
    response = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": True},
        headers=en_revision["ana"],
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_historial_completo(client, en_revision):
    # Dado que una tarea tuvo una entrega devuelta y luego una aprobada
    devuelta = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": False, "comment": DEVOLUCION},
        headers=en_revision["lider"],
    )
    assert devuelta.status_code == 200, devuelta.text

    segunda = await client.post(
        f"/api/v1/tasks/{en_revision['task']['id']}/submissions",
        json={"description": SEGUNDA_ENTREGA},
        headers=en_revision["ana"],
    )
    assert segunda.status_code == 201, segunda.text
    aprobada = await client.post(
        f"/api/v1/submissions/{segunda.json()['id']}/review",
        json={"approved": True, "comment": "Ahora sí, gracias."},
        headers=en_revision["lider"],
    )
    assert aprobada.status_code == 200, aprobada.text

    # Cuando consulto sus entregas
    response = await client.get(
        f"/api/v1/tasks/{en_revision['task']['id']}/submissions",
        headers=en_revision["lider"],
    )

    # Entonces veo las dos, con sus fechas, revisores y comentarios
    assert response.status_code == 200
    entregas = {e["id"]: e for e in response.json()}
    assert len(entregas) == 2
    # Se buscan por identificador y no por posición: dentro de una sola
    # transacción de prueba, now() da el mismo created_at a las dos y el orden
    # empata. En producción cada entrega llega en su propia transacción.
    primera = entregas[en_revision["submission"]["id"]]
    ultima = entregas[segunda.json()["id"]]
    assert primera["review_status"] == "REJECTED"
    assert primera["review_comment"] == DEVOLUCION
    assert ultima["review_status"] == "APPROVED"
    for entrega in (primera, ultima):
        assert entrega["reviewed_at"] is not None
        assert entrega["reviewed_by"]["email"] == "carlos@ejemplo.com"


@pytest.mark.asyncio
async def test_revisar_dos_veces_la_misma_entrega(client, en_revision):
    """La segunda revisión no reabre nada: la entrega ya se resolvió."""
    primera = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": True},
        headers=en_revision["lider"],
    )
    assert primera.status_code == 200, primera.text

    segunda = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": True},
        headers=en_revision["lider"],
    )
    assert segunda.status_code == 409
    assert segunda.json()["error"]["code"] == "SUBMISSION_ALREADY_REVIEWED"


@pytest.mark.asyncio
async def test_editar_la_entrega_propia_sin_revisar(client, en_revision):
    """RN-12: el autor corrige mientras nadie la haya mirado."""
    response = await client.patch(
        f"/api/v1/submissions/{en_revision['submission']['id']}",
        json={"description": SEGUNDA_ENTREGA, "commit_url": None},
        headers=en_revision["ana"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["description"] == SEGUNDA_ENTREGA
    assert response.json()["commit_url"] is None


@pytest.mark.asyncio
async def test_editar_la_entrega_ajena(client, en_revision):
    """El revisor puede aprobarla o devolverla, no reescribirla (RN-12)."""
    response = await client.patch(
        f"/api/v1/submissions/{en_revision['submission']['id']}",
        json={"description": SEGUNDA_ENTREGA},
        headers=en_revision["lider"],
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_editar_la_entrega_ya_revisada(client, en_revision):
    revisada = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": False, "comment": DEVOLUCION},
        headers=en_revision["lider"],
    )
    assert revisada.status_code == 200, revisada.text

    response = await client.patch(
        f"/api/v1/submissions/{en_revision['submission']['id']}",
        json={"description": SEGUNDA_ENTREGA},
        headers=en_revision["ana"],
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBMISSION_ALREADY_REVIEWED"


@pytest.mark.asyncio
async def test_entrega_de_otro_proyecto_no_existe(
    client, en_revision, make_user, make_project, auth_header
):
    """Un 404, no un 403: un 403 confirmaría que la entrega existe."""
    ajena = await make_user(email="ajena@ejemplo.com", full_name="Ajena")
    await make_project(name="Otro proyecto", leader_id=ajena.id)
    headers = await auth_header("ajena@ejemplo.com", PASSWORD)

    response = await client.post(
        f"/api/v1/submissions/{en_revision['submission']['id']}/review",
        json={"approved": True},
        headers=headers,
    )

    assert response.status_code == 404
