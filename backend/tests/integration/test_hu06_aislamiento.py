"""HU-06 — Aislamiento entre proyectos (RN-03, RN-04).

The user story writes the first scenario in terms of creating a task. Tasks
arrive in Phase 3, so the same claim is made with the write operation this phase
does have — creating a custom role, which needs role.manage exactly the way
creating a task will need task.create. The scenario names are kept so the file
can be pointed back at the task version once Phase 3 lands.
"""

import pytest

PASSWORD = "unaClaveLarga123"


@pytest.mark.asyncio
async def test_lider_en_un_proyecto_colaborador_en_otro(
    client, make_user, make_project, auth_header, get_roles
):
    # Dado que soy "Líder" del proyecto A y "Colaborador" del proyecto B
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana")
    otra = await make_user(email="otra@ejemplo.com", full_name="Otra Líder")

    proyecto_a = await make_project(name="Proyecto A", leader_id=ana.id)
    proyecto_b = await make_project(name="Proyecto B", leader_id=otra.id)

    otra_headers = await auth_header("otra@ejemplo.com", PASSWORD)
    roles_b = await get_roles(proyecto_b["id"], otra_headers)
    await client.post(
        f"/api/v1/projects/{proyecto_b['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": roles_b["Colaborador"]["id"]},
        headers=otra_headers,
    )

    ana_headers = await auth_header("ana@ejemplo.com", PASSWORD)

    # Cuando intento escribir en el proyecto A, la operación tiene éxito
    en_a = await client.post(
        f"/api/v1/projects/{proyecto_a['id']}/roles",
        json={"name": "Revisor", "color": "#B8860B", "permissions": ["task.view"]},
        headers=ana_headers,
    )
    assert en_a.status_code == 201, en_a.text

    # Cuando intento lo mismo en el proyecto B, recibo un error 403
    en_b = await client.post(
        f"/api/v1/projects/{proyecto_b['id']}/roles",
        json={"name": "Revisor", "color": "#B8860B", "permissions": ["task.view"]},
        headers=ana_headers,
    )
    assert en_b.status_code == 403
    assert en_b.json()["error"]["code"] == "FORBIDDEN"

    # Ser líder en A no aporta un solo permiso en B (RN-04).
    detalle_b = await client.get(f"/api/v1/projects/{proyecto_b['id']}", headers=ana_headers)
    assert sorted(detalle_b.json()["my_permissions"]) == ["task.comment", "task.view"]


@pytest.mark.asyncio
async def test_proyecto_ajeno(client, make_user, make_project, auth_header):
    # Dado que no soy miembro del proyecto C
    await make_user(email="ana@ejemplo.com")
    tercera = await make_user(email="tercera@ejemplo.com")
    proyecto_c = await make_project(name="Proyecto C", leader_id=tercera.id)
    headers = await auth_header("ana@ejemplo.com", PASSWORD)

    # Cuando solicito el detalle del proyecto C
    response = await client.get(f"/api/v1/projects/{proyecto_c['id']}", headers=headers)

    # Entonces recibo un error 404 y no un 403
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_la_lista_solo_muestra_los_proyectos_propios(
    client, make_user, make_project, auth_header
):
    ana = await make_user(email="ana@ejemplo.com")
    tercera = await make_user(email="tercera@ejemplo.com")
    mio = await make_project(name="Proyecto propio", leader_id=ana.id)
    await make_project(name="Proyecto ajeno", leader_id=tercera.id)
    headers = await auth_header("ana@ejemplo.com", PASSWORD)

    response = await client.get("/api/v1/projects", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [p["id"] for p in body["items"]] == [mio["id"]]
    assert body["items"][0]["my_role"]["name"] == "Líder"
    assert body["items"][0]["member_count"] == 1


@pytest.mark.asyncio
async def test_el_admin_global_ve_todos_los_proyectos_en_la_lista(
    client, make_user, make_project, admin_headers
):
    """RN-01: read access to everything, so the administrator can supervise."""
    ana = await make_user(email="ana@ejemplo.com")
    tercera = await make_user(email="tercera@ejemplo.com")
    await make_project(name="Proyecto uno", leader_id=ana.id)
    await make_project(name="Proyecto dos", leader_id=tercera.id)

    response = await client.get("/api/v1/projects", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["total"] == 2
    # The admin belongs to neither, so no role comes back.
    assert all(item["my_role"] is None for item in response.json()["items"])


@pytest.mark.asyncio
async def test_los_miembros_de_un_proyecto_ajeno_no_se_listan(
    client, make_user, make_project, auth_header
):
    await make_user(email="ana@ejemplo.com")
    tercera = await make_user(email="tercera@ejemplo.com")
    ajeno = await make_project(name="Proyecto ajeno", leader_id=tercera.id)
    headers = await auth_header("ana@ejemplo.com", PASSWORD)

    for path in ("members", "roles"):
        response = await client.get(
            f"/api/v1/projects/{ajeno['id']}/{path}", headers=headers
        )
        assert response.status_code == 404, path
