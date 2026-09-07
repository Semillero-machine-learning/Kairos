"""Lista, detalle, edición y archivado de proyectos (RF-13, RF-18, RF-19)."""

import pytest
import pytest_asyncio

PASSWORD = "unaClaveLarga123"


@pytest_asyncio.fixture
async def proyecto(make_user, make_project, auth_header):
    lider = await make_user(email="lider@ejemplo.com", full_name="Lider Principal")
    project = await make_project(
        name="Detección de anomalías",
        leader_id=lider.id,
        description="Modelos sobre series de tiempo.",
    )
    headers = await auth_header("lider@ejemplo.com", PASSWORD)
    return project, headers, lider


@pytest.mark.asyncio
async def test_el_detalle_trae_los_permisos_propios(client, proyecto):
    """The frontend needs my_permissions to decide what to show; the backend
    checks the same set again on every write anyway."""
    project, headers, _ = proyecto

    response = await client.get(f"/api/v1/projects/{project['id']}", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Detección de anomalías"
    assert body["member_count"] == 1
    assert body["my_role"]["name"] == "Líder"
    assert body["my_role"]["color"] == "#1F6F5C"
    assert len(body["my_permissions"]) == 14
    # Zero-filled until Phase 3 brings the tasks module.
    assert body["task_counts"] == {
        "BACKLOG": 0,
        "TODO": 0,
        "IN_PROGRESS": 0,
        "IN_REVIEW": 0,
        "DONE": 0,
    }


@pytest.mark.asyncio
async def test_editar_el_proyecto(client, proyecto):
    project, headers, _ = proyecto

    response = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Detección de anomalías v2", "start_date": "2026-10-01"},
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Detección de anomalías v2"
    assert body["start_date"] == "2026-10-01"
    # An omitted field is left alone: a PATCH never blanks what it does not carry.
    assert body["description"] == "Modelos sobre series de tiempo."


@pytest.mark.asyncio
async def test_un_nombre_demasiado_corto_se_rechaza(client, proyecto):
    project, headers, _ = proyecto

    response = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"name": "ML"}, headers=headers
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sin_project_edit_no_se_edita(client, proyecto, make_user, auth_header, get_roles):
    project, headers, _ = proyecto
    roles = await get_roles(project["id"], headers)
    ana = await make_user(email="ana@ejemplo.com")
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": roles["Colaborador"]["id"]},
        headers=headers,
    )
    ana_headers = await auth_header("ana@ejemplo.com", PASSWORD)

    response = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"name": "Otro nombre"}, headers=ana_headers
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_archivar_dos_veces_se_rechaza(client, proyecto):
    project, headers, _ = proyecto
    first = await client.post(f"/api/v1/projects/{project['id']}/archive", headers=headers)
    assert first.status_code == 200

    second = await client.post(f"/api/v1/projects/{project['id']}/archive", headers=headers)

    assert second.status_code == 409


@pytest.mark.asyncio
async def test_desarchivar_un_proyecto_activo_se_rechaza(client, proyecto):
    project, headers, _ = proyecto

    response = await client.post(
        f"/api/v1/projects/{project['id']}/unarchive", headers=headers
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_filtrar_la_lista_por_estado(client, proyecto, make_user, make_project):
    project, headers, lider = proyecto
    otro = await make_project(name="Proyecto vigente", leader_id=lider.id)
    await client.post(f"/api/v1/projects/{project['id']}/archive", headers=headers)

    archivados = await client.get("/api/v1/projects?status=ARCHIVED", headers=headers)
    activos = await client.get("/api/v1/projects?status=ACTIVE", headers=headers)
    todos = await client.get("/api/v1/projects", headers=headers)

    assert [p["id"] for p in archivados.json()["items"]] == [project["id"]]
    assert [p["id"] for p in activos.json()["items"]] == [otro["id"]]
    assert todos.json()["total"] == 2


@pytest.mark.asyncio
async def test_la_lista_se_pagina(client, make_user, make_project, auth_header):
    lider = await make_user(email="lider@ejemplo.com")
    for index in range(3):
        await make_project(name=f"Proyecto {index}", leader_id=lider.id)
    headers = await auth_header("lider@ejemplo.com", PASSWORD)

    response = await client.get("/api/v1/projects?page=2&size=2", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 2
    assert body["size"] == 2
    assert len(body["items"]) == 1


@pytest.mark.asyncio
async def test_el_catalogo_de_permisos_esta_disponible(client, proyecto):
    """Any authenticated user reads it: it is what the role editor is built on."""
    _, headers, _ = proyecto

    response = await client.get("/api/v1/permissions", headers=headers)

    assert response.status_code == 200
    catalog = response.json()
    assert len(catalog) == 14
    assert {p["category"] for p in catalog} == {"task", "member", "role", "project"}
    view = next(p for p in catalog if p["code"] == "task.view")
    assert view["description"]


@pytest.mark.asyncio
async def test_el_catalogo_exige_autenticacion(client):
    response = await client.get("/api/v1/permissions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_el_nombre_no_se_puede_dejar_en_nulo(client, proyecto):
    """`name` es NOT NULL: un null explícito se rechaza aquí, no en la base."""
    project, headers, _ = proyecto
    response = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"name": None}, headers=headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_las_fechas_y_la_descripcion_si_se_pueden_vaciar(client, proyecto):
    """A diferencia del nombre, estas columnas sí admiten nulo."""
    project, headers, _ = proyecto
    response = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"description": None, "start_date": None},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["description"] is None
    assert response.json()["start_date"] is None


@pytest.mark.asyncio
async def test_un_nombre_de_solo_espacios_se_rechaza(client, proyecto):
    """Se recorta antes de medir: si no, «   ab   » pasaría el mínimo de 3 y
    llegaría a la base con 2 caracteres."""
    project, headers, _ = proyecto
    response = await client.patch(
        f"/api/v1/projects/{project['id']}", json={"name": "   ab   "}, headers=headers
    )
    assert response.status_code == 422
