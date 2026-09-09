"""HU-12 — Publicar material de estudio (RF-46 a RF-51, RN-31, RN-33).

Scenario names mirror docs/user-stories.md.
"""

import pytest

PASSWORD = "unaClaveLarga123"


@pytest.mark.asyncio
async def test_creacion_en_borrador(client, editor_headers, member_headers):
    # Dado que tengo el rol global "LESSON_EDITOR"
    # Cuando creo el módulo "Redes neuronales"
    response = await client.post(
        "/api/v1/lesson-modules",
        json={"title": "Redes neuronales"},
        headers=editor_headers,
    )

    # Entonces queda en estado borrador
    assert response.status_code == 201, response.text
    assert response.json()["is_published"] is False

    # Y no es visible para los usuarios con rol "MEMBER"
    catalogo = await client.get("/api/v1/lesson-modules", headers=member_headers)
    assert catalogo.json() == []


@pytest.mark.asyncio
async def test_publicacion(client, editor_headers, member_headers, make_module):
    # Dado que el módulo tiene 3 lecciones publicadas
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    for title in ("Perceptrón", "Retropropagación", "Regularización"):
        creada = await client.post(
            f"/api/v1/lesson-modules/{module['id']}/lessons",
            json={"title": title},
            headers=editor_headers,
        )
        await client.post(
            f"/api/v1/lessons/{creada.json()['id']}/publish",
            json={"published": True},
            headers=editor_headers,
        )

    # Cuando publico el módulo
    response = await client.post(
        f"/api/v1/lesson-modules/{module['id']}/publish",
        json={"published": True},
        headers=editor_headers,
    )
    assert response.status_code == 200, response.text

    # Entonces todos los usuarios autenticados pueden verlo
    catalogo = await client.get("/api/v1/lesson-modules", headers=member_headers)
    body = catalogo.json()
    assert [m["title"] for m in body] == ["Redes neuronales"]
    assert len(body[0]["lessons"]) == 3


@pytest.mark.asyncio
async def test_leccion_publicada_dentro_de_modulo_en_borrador(
    client, editor_headers, member_headers, make_module
):
    # Dado que el módulo está en borrador
    module = await make_module(title="Series de tiempo", headers=editor_headers)

    # Y contiene una lección publicada
    creada = await client.post(
        f"/api/v1/lesson-modules/{module['id']}/lessons",
        json={"title": "Estacionalidad"},
        headers=editor_headers,
    )
    lesson_id = creada.json()["id"]
    await client.post(
        f"/api/v1/lessons/{lesson_id}/publish",
        json={"published": True},
        headers=editor_headers,
    )

    # Cuando un usuario con rol "MEMBER" consulta el catálogo
    catalogo = await client.get("/api/v1/lesson-modules", headers=member_headers)

    # Entonces no ve ni el módulo ni la lección
    assert catalogo.json() == []
    # Y tampoco llegando a la lección por su dirección directa: el módulo manda
    # (RN-33), y «no visible» tiene que leerse igual que «no existe».
    directa = await client.get(f"/api/v1/lessons/{lesson_id}", headers=member_headers)
    assert directa.status_code == 404


@pytest.mark.asyncio
async def test_un_lider_de_proyecto_intenta_publicar(
    client, make_user, make_project, auth_header
):
    # Dado que soy líder de un proyecto con rol global "MEMBER"
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)

    # Cuando intento crear un módulo de lecciones
    response = await client.post(
        "/api/v1/lesson-modules", json={"title": "Módulo del líder"}, headers=lider
    )

    # Entonces recibo un error 403
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_recursos_enlazados(client, editor_headers, make_module):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    creada = await client.post(
        f"/api/v1/lesson-modules/{module['id']}/lessons",
        json={"title": "Perceptrón"},
        headers=editor_headers,
    )
    lesson_id = creada.json()["id"]

    # Cuando agrego a una lección un recurso de tipo "NOTEBOOK"
    #      con la URL del repositorio del semillero
    response = await client.post(
        f"/api/v1/lessons/{lesson_id}/resources",
        json={
            "type": "NOTEBOOK",
            "title": "Cuaderno del perceptrón",
            "url": "https://github.com/semillero-ml/redes/blob/main/perceptron.ipynb",
        },
        headers=editor_headers,
    )

    # Entonces el recurso queda enlazado
    assert response.status_code == 201, response.text
    detalle = await client.get(f"/api/v1/lessons/{lesson_id}", headers=editor_headers)
    recursos = detalle.json()["resources"]
    assert len(recursos) == 1
    assert recursos[0]["type"] == "NOTEBOOK"

    # Y no se almacena ningún archivo en la plataforma: lo único que se guarda
    # es la dirección, y tiene que ser externa (RN-34).
    assert recursos[0]["url"].startswith("https://github.com/")
    local = await client.post(
        f"/api/v1/lessons/{lesson_id}/resources",
        json={"type": "NOTEBOOK", "title": "Copia", "url": "/archivos/perceptron.ipynb"},
        headers=editor_headers,
    )
    assert local.status_code == 422


@pytest.mark.asyncio
async def test_eliminacion_de_modulo_con_contenido(client, editor_headers, make_module):
    # Dado que el módulo tiene 3 lecciones
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    for title in ("Perceptrón", "Retropropagación", "Regularización"):
        await client.post(
            f"/api/v1/lesson-modules/{module['id']}/lessons",
            json={"title": title},
            headers=editor_headers,
        )

    # Cuando intento eliminarlo sin confirmación
    response = await client.delete(
        f"/api/v1/lesson-modules/{module['id']}", headers=editor_headers
    )

    # Entonces recibo un error 409 indicando que se perderían 3 lecciones
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "CONFIRMATION_REQUIRED"
    assert error["details"] == {"lessons": 3}
    assert "3 lecciones" in error["message"]

    # Y el módulo sigue ahí: el aviso no borra nada.
    catalogo = await client.get("/api/v1/lesson-modules", headers=editor_headers)
    assert len(catalogo.json()) == 1
