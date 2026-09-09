"""Módulos del catálogo: quién los escribe, quién los ve y en qué orden.

Cubre RF-46, RF-47, RF-49 a RF-51 y RN-31, RN-32, RN-36.
"""

import pytest

from app.core.enums import GlobalRole

PASSWORD = "unaClaveLarga123"


@pytest.mark.asyncio
async def test_el_modulo_nace_en_borrador(client, editor_headers):
    """RF-49: nada llega al semillero hasta que un editor lo decide."""
    response = await client.post(
        "/api/v1/lesson-modules",
        json={"title": "Redes neuronales", "description": "De cero a una red que entrena."},
        headers=editor_headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["is_published"] is False
    assert body["position"] == 0
    assert body["lessons"] == []


@pytest.mark.asyncio
async def test_un_miembro_no_ve_los_borradores(client, editor_headers, member_headers, make_module):
    """RN-32: el borrador es del editor y de nadie más."""
    await make_module(title="Módulo en borrador", headers=editor_headers)

    del_editor = await client.get("/api/v1/lesson-modules", headers=editor_headers)
    del_miembro = await client.get("/api/v1/lesson-modules", headers=member_headers)

    assert len(del_editor.json()) == 1
    assert del_miembro.json() == []


@pytest.mark.asyncio
async def test_publicar_lo_hace_visible(client, editor_headers, member_headers, make_module):
    module = await make_module(title="Módulo listo", headers=editor_headers)

    published = await client.post(
        f"/api/v1/lesson-modules/{module['id']}/publish",
        json={"published": True},
        headers=editor_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["is_published"] is True

    visible = await client.get("/api/v1/lesson-modules", headers=member_headers)
    assert [m["title"] for m in visible.json()] == ["Módulo listo"]


@pytest.mark.asyncio
async def test_despublicar_lo_vuelve_a_esconder(
    client, editor_headers, member_headers, make_module
):
    """RF-47 nombra las dos direcciones, no solo publicar."""
    module = await make_module(title="Módulo temporal", headers=editor_headers, published=True)

    withdrawn = await client.post(
        f"/api/v1/lesson-modules/{module['id']}/publish",
        json={"published": False},
        headers=editor_headers,
    )

    assert withdrawn.json()["is_published"] is False
    visible = await client.get("/api/v1/lesson-modules", headers=member_headers)
    assert visible.json() == []


@pytest.mark.asyncio
async def test_el_administrador_tambien_edita_el_catalogo(client, admin_headers):
    """RN-31 nombra dos roles globales, no uno."""
    response = await client.post(
        "/api/v1/lesson-modules", json={"title": "Fundamentos"}, headers=admin_headers
    )

    assert response.status_code == 201, response.text


@pytest.mark.asyncio
async def test_un_miembro_no_puede_crear_modulos(client, member_headers):
    response = await client.post(
        "/api/v1/lesson-modules", json={"title": "Módulo pirata"}, headers=member_headers
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_el_titulo_corto_no_pasa(client, editor_headers):
    response = await client.post(
        "/api/v1/lesson-modules", json={"title": "ab"}, headers=editor_headers
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_el_patch_solo_toca_lo_que_trae(client, editor_headers, make_module):
    module = await make_module(
        title="Título original", description="Descripción original", headers=editor_headers
    )

    response = await client.patch(
        f"/api/v1/lesson-modules/{module['id']}",
        json={"title": "Título nuevo"},
        headers=editor_headers,
    )

    body = response.json()
    assert body["title"] == "Título nuevo"
    assert body["description"] == "Descripción original"


@pytest.mark.asyncio
async def test_el_patch_no_publica(client, editor_headers, make_module):
    """La publicación tiene su propio endpoint: un camino por decisión."""
    module = await make_module(title="Módulo cerrado", headers=editor_headers)

    response = await client.patch(
        f"/api/v1/lesson-modules/{module['id']}",
        json={"title": "Módulo cerrado", "is_published": True},
        headers=editor_headers,
    )

    assert response.json()["is_published"] is False


@pytest.mark.asyncio
async def test_los_modulos_nuevos_van_al_final(client, editor_headers, make_module):
    for title in ("Primero", "Segundo", "Tercero"):
        await make_module(title=title, headers=editor_headers)

    catalog = await client.get("/api/v1/lesson-modules", headers=editor_headers)

    assert [m["title"] for m in catalog.json()] == ["Primero", "Segundo", "Tercero"]
    assert [m["position"] for m in catalog.json()] == [0, 1, 2]


@pytest.mark.asyncio
async def test_reordenar_reescribe_las_posiciones(client, editor_headers, make_module):
    """RF-50: el orden lo define el editor a mano."""
    primero = await make_module(title="Primero", headers=editor_headers)
    segundo = await make_module(title="Segundo", headers=editor_headers)
    tercero = await make_module(title="Tercero", headers=editor_headers)

    response = await client.post(
        "/api/v1/lesson-modules/reorder",
        json={"ids": [tercero["id"], primero["id"], segundo["id"]]},
        headers=editor_headers,
    )

    assert response.status_code == 200, response.text
    assert [m["title"] for m in response.json()] == ["Tercero", "Primero", "Segundo"]
    assert [m["position"] for m in response.json()] == [0, 1, 2]


@pytest.mark.asyncio
async def test_reordenar_con_la_lista_incompleta_falla(client, editor_headers, make_module):
    """Una lista parcial obligaría a adivinar dónde va el resto, y la adivinanza
    saldría mal justo cuando importa: cuando otro editor agregó algo."""
    primero = await make_module(title="Primero", headers=editor_headers)
    await make_module(title="Segundo", headers=editor_headers)

    response = await client.post(
        "/api/v1/lesson-modules/reorder",
        json={"ids": [primero["id"]]},
        headers=editor_headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_reordenar_con_repetidos_falla(client, editor_headers, make_module):
    primero = await make_module(title="Primero", headers=editor_headers)

    response = await client.post(
        "/api/v1/lesson-modules/reorder",
        json={"ids": [primero["id"], primero["id"]]},
        headers=editor_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_borrar_sin_confirmar_avisa(client, editor_headers, make_module):
    """RN-36: la interfaz tiene que poder decir el número exacto."""
    module = await make_module(title="Módulo vacío", headers=editor_headers)

    response = await client.delete(f"/api/v1/lesson-modules/{module['id']}")

    assert response.status_code == 401  # sin credenciales, antes que nada

    response = await client.delete(
        f"/api/v1/lesson-modules/{module['id']}", headers=editor_headers
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "CONFIRMATION_REQUIRED"
    assert error["details"] == {"lessons": 0}


@pytest.mark.asyncio
async def test_borrar_confirmado_lo_elimina(client, editor_headers, make_module):
    module = await make_module(title="Módulo desechable", headers=editor_headers)

    response = await client.delete(
        f"/api/v1/lesson-modules/{module['id']}?confirm=true", headers=editor_headers
    )

    assert response.status_code == 204
    catalog = await client.get("/api/v1/lesson-modules", headers=editor_headers)
    assert catalog.json() == []


@pytest.mark.asyncio
async def test_un_modulo_inexistente_es_404(client, editor_headers):
    ausente = "00000000-0000-0000-0000-000000000000"

    response = await client.patch(
        f"/api/v1/lesson-modules/{ausente}", json={"title": "Da igual"}, headers=editor_headers
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_la_busqueda_encuentra_por_titulo_y_descripcion(
    client, editor_headers, member_headers, make_module
):
    """RF-51: buscar por título o descripción, sin distinguir mayúsculas."""
    await make_module(
        title="Redes neuronales",
        description="Perceptrón y retropropagación.",
        headers=editor_headers,
        published=True,
    )
    await make_module(title="Series de tiempo", headers=editor_headers, published=True)

    por_titulo = await client.get(
        "/api/v1/lesson-modules", params={"q": "REDES"}, headers=member_headers
    )
    por_descripcion = await client.get(
        "/api/v1/lesson-modules", params={"q": "perceptrón"}, headers=member_headers
    )
    sin_resultados = await client.get(
        "/api/v1/lesson-modules", params={"q": "transformers"}, headers=member_headers
    )

    assert [m["title"] for m in por_titulo.json()] == ["Redes neuronales"]
    assert [m["title"] for m in por_descripcion.json()] == ["Redes neuronales"]
    assert sin_resultados.json() == []


@pytest.mark.asyncio
async def test_la_busqueda_no_revela_borradores(
    client, editor_headers, member_headers, make_module
):
    """La visibilidad se aplica antes que el texto: al revés, la forma de la
    respuesta delataría que el borrador existe."""
    await make_module(title="Transformers", headers=editor_headers)

    response = await client.get(
        "/api/v1/lesson-modules", params={"q": "transformers"}, headers=member_headers
    )

    assert response.json() == []


@pytest.mark.asyncio
async def test_el_catalogo_exige_sesion(client):
    response = await client.get("/api/v1/lesson-modules")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_un_usuario_desactivado_no_llega_al_catalogo(
    client, make_user, auth_header, db
):
    from app.core.enums import UserStatus

    user = await make_user(email="saliente@ejemplo.com", global_role=GlobalRole.LESSON_EDITOR)
    headers = await auth_header("saliente@ejemplo.com", PASSWORD)
    user.status = UserStatus.DISABLED
    await db.flush()

    response = await client.get("/api/v1/lesson-modules", headers=headers)

    assert response.status_code == 401
