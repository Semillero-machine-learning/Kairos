"""Lecciones y recursos: visibilidad, enlaces y orden.

Cubre RF-46, RF-48, RF-50, RF-51 y RN-31, RN-33, RN-34.
"""

import pytest

AUSENTE = "00000000-0000-0000-0000-000000000000"


@pytest.fixture
def make_lesson(client):
    async def _make(
        module_id: str,
        headers: dict[str, str],
        *,
        title: str = "Perceptrón",
        description: str | None = None,
        published: bool = False,
    ) -> dict:
        response = await client.post(
            f"/api/v1/lesson-modules/{module_id}/lessons",
            json={"title": title, "description": description},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        lesson = response.json()
        if published:
            published_response = await client.post(
                f"/api/v1/lessons/{lesson['id']}/publish",
                json={"published": True},
                headers=headers,
            )
            assert published_response.status_code == 200, published_response.text
            lesson = published_response.json()
        return lesson

    return _make


@pytest.mark.asyncio
async def test_la_leccion_nace_en_borrador(client, editor_headers, make_module, make_lesson):
    module = await make_module(title="Redes neuronales", headers=editor_headers)

    lesson = await make_lesson(module["id"], editor_headers, title="Perceptrón")

    assert lesson["is_published"] is False
    assert lesson["position"] == 0
    assert lesson["resource_count"] == 0
    assert lesson["module_id"] == module["id"]


@pytest.mark.asyncio
async def test_el_modulo_manda_sobre_la_leccion(
    client, editor_headers, member_headers, make_module, make_lesson
):
    """RN-33: una lección publicada dentro de un módulo en borrador no existe
    para quien no edita."""
    module = await make_module(title="Módulo en preparación", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers, published=True)

    en_catalogo = await client.get("/api/v1/lesson-modules", headers=member_headers)
    directa = await client.get(f"/api/v1/lessons/{lesson['id']}", headers=member_headers)

    assert en_catalogo.json() == []
    assert directa.status_code == 404
    assert directa.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_la_leccion_en_borrador_no_se_ve_en_modulo_publicado(
    client, editor_headers, member_headers, make_module, make_lesson
):
    """RN-32, el otro sentido: el módulo está publicado, la lección no."""
    module = await make_module(title="Módulo abierto", headers=editor_headers, published=True)
    await make_lesson(module["id"], editor_headers, title="Lista", published=True)
    borrador = await make_lesson(module["id"], editor_headers, title="A medias")

    catalogo = await client.get("/api/v1/lesson-modules", headers=member_headers)
    directa = await client.get(f"/api/v1/lessons/{borrador['id']}", headers=member_headers)

    assert [le["title"] for le in catalogo.json()[0]["lessons"]] == ["Lista"]
    assert directa.status_code == 404


@pytest.mark.asyncio
async def test_el_editor_si_ve_los_borradores(
    client, editor_headers, make_module, make_lesson
):
    module = await make_module(title="Módulo abierto", headers=editor_headers, published=True)
    borrador = await make_lesson(module["id"], editor_headers, title="A medias")

    response = await client.get(f"/api/v1/lessons/{borrador['id']}", headers=editor_headers)

    assert response.status_code == 200
    assert response.json()["module_title"] == "Módulo abierto"


@pytest.mark.asyncio
async def test_publicar_la_leccion_no_publica_el_modulo(
    client, editor_headers, make_module, make_lesson
):
    module = await make_module(title="Módulo en preparación", headers=editor_headers)

    await make_lesson(module["id"], editor_headers, published=True)

    catalogo = await client.get("/api/v1/lesson-modules", headers=editor_headers)
    assert catalogo.json()[0]["is_published"] is False


@pytest.mark.asyncio
async def test_un_miembro_no_crea_lecciones(client, editor_headers, member_headers, make_module):
    module = await make_module(title="Redes neuronales", headers=editor_headers)

    response = await client.post(
        f"/api/v1/lesson-modules/{module['id']}/lessons",
        json={"title": "Lección pirata"},
        headers=member_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_una_leccion_en_un_modulo_inexistente_es_404(client, editor_headers):
    response = await client.post(
        f"/api/v1/lesson-modules/{AUSENTE}/lessons",
        json={"title": "Sin casa"},
        headers=editor_headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_las_lecciones_nuevas_van_al_final(
    client, editor_headers, make_module, make_lesson
):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    for title in ("Primera", "Segunda", "Tercera"):
        await make_lesson(module["id"], editor_headers, title=title)

    catalogo = await client.get("/api/v1/lesson-modules", headers=editor_headers)

    lessons = catalogo.json()[0]["lessons"]
    assert [le["title"] for le in lessons] == ["Primera", "Segunda", "Tercera"]
    assert [le["position"] for le in lessons] == [0, 1, 2]


@pytest.mark.asyncio
async def test_reordenar_lecciones(client, editor_headers, make_module, make_lesson):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    primera = await make_lesson(module["id"], editor_headers, title="Primera")
    segunda = await make_lesson(module["id"], editor_headers, title="Segunda")

    response = await client.post(
        f"/api/v1/lesson-modules/{module['id']}/lessons/reorder",
        json={"ids": [segunda["id"], primera["id"]]},
        headers=editor_headers,
    )

    assert response.status_code == 200, response.text
    assert [le["title"] for le in response.json()] == ["Segunda", "Primera"]
    assert [le["position"] for le in response.json()] == [0, 1]


@pytest.mark.asyncio
async def test_reordenar_lecciones_de_otro_modulo_falla(
    client, editor_headers, make_module, make_lesson
):
    """El orden se rehace dentro de un módulo; una lección ajena no cuenta."""
    uno = await make_module(title="Módulo uno", headers=editor_headers)
    otro = await make_module(title="Módulo otro", headers=editor_headers)
    propia = await make_lesson(uno["id"], editor_headers, title="Propia")
    ajena = await make_lesson(otro["id"], editor_headers, title="Ajena")

    response = await client.post(
        f"/api/v1/lesson-modules/{uno['id']}/lessons/reorder",
        json={"ids": [propia["id"], ajena["id"]]},
        headers=editor_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_borrar_la_leccion_la_saca_del_catalogo(
    client, editor_headers, make_module, make_lesson
):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)

    response = await client.delete(f"/api/v1/lessons/{lesson['id']}", headers=editor_headers)

    assert response.status_code == 204
    catalogo = await client.get("/api/v1/lesson-modules", headers=editor_headers)
    assert catalogo.json()[0]["lessons"] == []


# --- Recursos ---


@pytest.mark.asyncio
async def test_el_recurso_queda_enlazado(client, editor_headers, make_module, make_lesson):
    """RF-48 y RN-34: se guarda la dirección, no el archivo."""
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)

    response = await client.post(
        f"/api/v1/lessons/{lesson['id']}/resources",
        json={
            "type": "NOTEBOOK",
            "title": "Cuaderno del perceptrón",
            "url": "https://github.com/semillero-ml/redes/blob/main/perceptron.ipynb",
        },
        headers=editor_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["type"] == "NOTEBOOK"
    assert body["url"].startswith("https://github.com/")
    assert body["position"] == 0


@pytest.mark.asyncio
async def test_los_cinco_tipos_de_recurso_valen(
    client, editor_headers, make_module, make_lesson
):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)

    for kind in ("NOTEBOOK", "PDF", "VIDEO", "REPOSITORY", "ARTICLE"):
        response = await client.post(
            f"/api/v1/lessons/{lesson['id']}/resources",
            json={"type": kind, "title": kind.title(), "url": "https://ejemplo.com/x"},
            headers=editor_headers,
        )
        assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_un_tipo_inventado_no_pasa(client, editor_headers, make_module, make_lesson):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)

    response = await client.post(
        f"/api/v1/lessons/{lesson['id']}/resources",
        json={"type": "PODCAST", "title": "Episodio", "url": "https://ejemplo.com/x"},
        headers=editor_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_una_url_que_no_es_externa_no_pasa(
    client, editor_headers, make_module, make_lesson
):
    """RN-34: la plataforma no aloja archivos, así que no hay rutas locales."""
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)

    for url in ("/archivos/cuaderno.ipynb", "ftp://servidor/archivo", "javascript:alert(1)"):
        response = await client.post(
            f"/api/v1/lessons/{lesson['id']}/resources",
            json={"type": "NOTEBOOK", "title": "Cuaderno", "url": url},
            headers=editor_headers,
        )
        assert response.status_code == 422, url


@pytest.mark.asyncio
async def test_el_conteo_de_recursos_viaja_en_el_arbol(
    client, editor_headers, make_module, make_lesson
):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)
    for i in range(3):
        await client.post(
            f"/api/v1/lessons/{lesson['id']}/resources",
            json={"type": "ARTICLE", "title": f"Lectura {i}", "url": "https://ejemplo.com/x"},
            headers=editor_headers,
        )

    catalogo = await client.get("/api/v1/lesson-modules", headers=editor_headers)

    assert catalogo.json()[0]["lessons"][0]["resource_count"] == 3


@pytest.mark.asyncio
async def test_reordenar_recursos(client, editor_headers, make_module, make_lesson):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)
    creados = []
    for title in ("Primero", "Segundo"):
        response = await client.post(
            f"/api/v1/lessons/{lesson['id']}/resources",
            json={"type": "ARTICLE", "title": title, "url": "https://ejemplo.com/x"},
            headers=editor_headers,
        )
        creados.append(response.json())

    response = await client.post(
        f"/api/v1/lessons/{lesson['id']}/resources/reorder",
        json={"ids": [creados[1]["id"], creados[0]["id"]]},
        headers=editor_headers,
    )

    assert response.status_code == 200, response.text
    assert [r["title"] for r in response.json()] == ["Segundo", "Primero"]


@pytest.mark.asyncio
async def test_borrar_el_recurso_lo_desenlaza(
    client, editor_headers, make_module, make_lesson
):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)
    creado = await client.post(
        f"/api/v1/lessons/{lesson['id']}/resources",
        json={"type": "VIDEO", "title": "Clase grabada", "url": "https://ejemplo.com/v"},
        headers=editor_headers,
    )

    response = await client.delete(
        f"/api/v1/resources/{creado.json()['id']}", headers=editor_headers
    )

    assert response.status_code == 204
    detalle = await client.get(f"/api/v1/lessons/{lesson['id']}", headers=editor_headers)
    assert detalle.json()["resources"] == []


@pytest.mark.asyncio
async def test_un_miembro_no_borra_recursos(
    client, editor_headers, member_headers, make_module, make_lesson
):
    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)
    creado = await client.post(
        f"/api/v1/lessons/{lesson['id']}/resources",
        json={"type": "VIDEO", "title": "Clase grabada", "url": "https://ejemplo.com/v"},
        headers=editor_headers,
    )

    response = await client.delete(
        f"/api/v1/resources/{creado.json()['id']}", headers=member_headers
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_los_recursos_salen_en_orden_en_el_detalle(
    client, editor_headers, member_headers, make_module, make_lesson
):
    module = await make_module(title="Redes neuronales", headers=editor_headers, published=True)
    lesson = await make_lesson(module["id"], editor_headers, published=True)
    for title in ("Uno", "Dos", "Tres"):
        await client.post(
            f"/api/v1/lessons/{lesson['id']}/resources",
            json={"type": "ARTICLE", "title": title, "url": "https://ejemplo.com/x"},
            headers=editor_headers,
        )

    detalle = await client.get(f"/api/v1/lessons/{lesson['id']}", headers=member_headers)

    assert [r["title"] for r in detalle.json()["resources"]] == ["Uno", "Dos", "Tres"]


@pytest.mark.asyncio
async def test_borrar_el_modulo_arrastra_lecciones_y_recursos(
    client, editor_headers, make_module, make_lesson, db
):
    """RN-36: la cascada la hace la base, no un bucle en Python."""
    from sqlalchemy import func, select

    from app.modules.lessons.models import Lesson, LessonResource

    module = await make_module(title="Redes neuronales", headers=editor_headers)
    lesson = await make_lesson(module["id"], editor_headers)
    await client.post(
        f"/api/v1/lessons/{lesson['id']}/resources",
        json={"type": "PDF", "title": "Diapositivas", "url": "https://ejemplo.com/d.pdf"},
        headers=editor_headers,
    )

    response = await client.delete(
        f"/api/v1/lesson-modules/{module['id']}?confirm=true", headers=editor_headers
    )

    assert response.status_code == 204
    lecciones = await db.execute(select(func.count()).select_from(Lesson))
    recursos = await db.execute(select(func.count()).select_from(LessonResource))
    assert lecciones.scalar_one() == 0
    assert recursos.scalar_one() == 0


@pytest.mark.asyncio
async def test_la_busqueda_encuentra_lecciones_dentro_del_modulo(
    client, editor_headers, member_headers, make_module, make_lesson
):
    """Un módulo que no casa sobrevive por sus lecciones, y muestra solo esas."""
    module = await make_module(title="Fundamentos", headers=editor_headers, published=True)
    await make_lesson(module["id"], editor_headers, title="Retropropagación", published=True)
    await make_lesson(module["id"], editor_headers, title="Regresión lineal", published=True)

    response = await client.get(
        "/api/v1/lesson-modules", params={"q": "retropropagación"}, headers=member_headers
    )

    body = response.json()
    assert [m["title"] for m in body] == ["Fundamentos"]
    assert [le["title"] for le in body[0]["lessons"]] == ["Retropropagación"]
