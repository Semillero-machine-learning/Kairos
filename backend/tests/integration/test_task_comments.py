"""Comentarios de tarea (RF-35, RN-11).

HU-09 no trae escenarios Gherkin para el hilo de comentarios; el criterio de
aceptación es RF-35 y la regla de propiedad RN-11, y eso es lo que se comprueba
aquí, endpoint por endpoint.
"""

import pytest
import pytest_asyncio

PASSWORD = "unaClaveLarga123"


@pytest_asyncio.fixture
async def hilo(make_user, make_project, auth_header, add_member, make_task):
    """Un proyecto con una tarea y dos colaboradores.

    El rol Colaborador trae "task.comment" pero no "task.delete", así que Luis
    sirve para el caso del que no es autor y tampoco modera.
    """
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    luis = await make_user(email="luis@ejemplo.com", full_name="Luis Pérez")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)

    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)
    await add_member(project["id"], luis.id, "Colaborador", lider)
    task = await make_task(project["id"], lider, assignee_ids=(ana.id,))

    return {
        "project": project,
        "task": task,
        "lider": lider,
        "ana": await auth_header("ana@ejemplo.com", PASSWORD),
        "luis": await auth_header("luis@ejemplo.com", PASSWORD),
    }


async def _comentar(client, hilo, texto: str, headers: dict[str, str]) -> dict:
    response = await client.post(
        f"/api/v1/tasks/{hilo['task']['id']}/comments",
        json={"body": texto},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_comentar_y_leer_el_hilo(client, hilo):
    await _comentar(client, hilo, "¿Usamos los datos de agosto o los de julio?", hilo["ana"])
    await _comentar(client, hilo, "Los de agosto, ya están limpios.", hilo["lider"])

    response = await client.get(
        f"/api/v1/tasks/{hilo['task']['id']}/comments", headers=hilo["luis"]
    )

    assert response.status_code == 200, response.text
    cuerpo = response.json()
    # Más antiguo primero: una conversación se lee hacia abajo.
    assert [c["body"] for c in cuerpo] == [
        "¿Usamos los datos de agosto o los de julio?",
        "Los de agosto, ya están limpios.",
    ]
    assert cuerpo[0]["author"]["email"] == "ana@ejemplo.com"


@pytest.mark.asyncio
async def test_comentario_vacio(client, hilo):
    response = await client.post(
        f"/api/v1/tasks/{hilo['task']['id']}/comments",
        json={"body": "   "},
        headers=hilo["ana"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_editar_el_comentario_propio(client, hilo):
    comentario = await _comentar(client, hilo, "Me equivoqué de cifra.", hilo["ana"])

    response = await client.patch(
        f"/api/v1/comments/{comentario['id']}",
        json={"body": "La exactitud fue 0.87, no 0.78."},
        headers=hilo["ana"],
    )

    assert response.status_code == 200, response.text
    assert response.json()["body"] == "La exactitud fue 0.87, no 0.78."


@pytest.mark.asyncio
async def test_editar_un_comentario_ajeno(client, hilo):
    """RN-11: nadie edita palabras de otro, ni siquiera el líder que modera."""
    comentario = await _comentar(client, hilo, "Yo dije esto.", hilo["ana"])

    response = await client.patch(
        f"/api/v1/comments/{comentario['id']}",
        json={"body": "Esto es lo que yo quisiera que hubiera dicho."},
        headers=hilo["lider"],
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_borrar_el_comentario_propio(client, hilo):
    comentario = await _comentar(client, hilo, "Mejor lo borro.", hilo["ana"])

    borrado = await client.delete(
        f"/api/v1/comments/{comentario['id']}", headers=hilo["ana"]
    )
    assert borrado.status_code == 204

    hilo_actual = await client.get(
        f"/api/v1/tasks/{hilo['task']['id']}/comments", headers=hilo["ana"]
    )
    assert hilo_actual.json() == []


@pytest.mark.asyncio
async def test_moderar_un_comentario_ajeno(client, hilo):
    """El líder tiene "task.delete": puede retirar un comentario ajeno (RN-11)."""
    comentario = await _comentar(client, hilo, "Comentario fuera de lugar.", hilo["ana"])

    borrado = await client.delete(
        f"/api/v1/comments/{comentario['id']}", headers=hilo["lider"]
    )

    assert borrado.status_code == 204


@pytest.mark.asyncio
async def test_borrar_un_comentario_ajeno_sin_moderar(client, hilo):
    """Luis es Colaborador: ni es el autor ni tiene "task.delete"."""
    comentario = await _comentar(client, hilo, "Comentario de Ana.", hilo["ana"])

    response = await client.delete(
        f"/api/v1/comments/{comentario['id']}", headers=hilo["luis"]
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_comentario_borrado_no_se_puede_editar(client, hilo):
    """El borrado es lógico, pero para la API el comentario ya no existe."""
    comentario = await _comentar(client, hilo, "Se va a borrar.", hilo["ana"])
    assert (
        await client.delete(f"/api/v1/comments/{comentario['id']}", headers=hilo["ana"])
    ).status_code == 204

    response = await client.patch(
        f"/api/v1/comments/{comentario['id']}",
        json={"body": "Resucitado."},
        headers=hilo["ana"],
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_comentario_de_otro_proyecto_no_existe(
    client, hilo, make_user, make_project, auth_header
):
    """404, no 403: un 403 confirmaría que el comentario existe."""
    comentario = await _comentar(client, hilo, "Comentario privado.", hilo["ana"])
    ajena = await make_user(email="ajena@ejemplo.com", full_name="Ajena")
    await make_project(name="Otro proyecto", leader_id=ajena.id)
    headers = await auth_header("ajena@ejemplo.com", PASSWORD)

    response = await client.patch(
        f"/api/v1/comments/{comentario['id']}",
        json={"body": "Intruso."},
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_observador_puede_comentar(client, hilo, make_user, add_member, auth_header):
    """El rol Observador trae "task.comment": mira y opina, no ejecuta."""
    sofia = await make_user(email="sofia@ejemplo.com", full_name="Sofía")
    await add_member(hilo["project"]["id"], sofia.id, "Observador", hilo["lider"])
    headers = await auth_header("sofia@ejemplo.com", PASSWORD)

    response = await client.post(
        f"/api/v1/tasks/{hilo['task']['id']}/comments",
        json={"body": "Ojo con el desbalance de clases."},
        headers=headers,
    )

    assert response.status_code == 201, response.text
