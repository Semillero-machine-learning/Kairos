"""Gestión de miembros del proyecto (RF-15, RF-16, RF-17, RN-14, EB-04)."""

import uuid

import pytest
import pytest_asyncio

from app.core.enums import UserStatus

PASSWORD = "unaClaveLarga123"


@pytest_asyncio.fixture
async def proyecto(make_user, make_project, auth_header, get_roles):
    lider = await make_user(email="lider@ejemplo.com", full_name="Lider Principal")
    project = await make_project(name="Detección de anomalías", leader_id=lider.id)
    headers = await auth_header("lider@ejemplo.com", PASSWORD)
    roles = await get_roles(project["id"], headers)
    return project, headers, lider, roles


@pytest.mark.asyncio
async def test_agregar_un_usuario_existente(client, proyecto, make_user):
    project, headers, _, roles = proyecto
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")

    response = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": roles["Colaborador"]["id"]},
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["full_name"] == "Ana Gómez"
    assert body["user"]["email"] == "ana@ejemplo.com"
    assert body["role"]["name"] == "Colaborador"

    members = await client.get(f"/api/v1/projects/{project['id']}/members", headers=headers)
    assert {m["user"]["email"] for m in members.json()} == {
        "lider@ejemplo.com",
        "ana@ejemplo.com",
    }


@pytest.mark.asyncio
async def test_no_se_agrega_dos_veces_a_la_misma_persona(client, proyecto, make_user):
    """RN-03: exactly one role per user per project."""
    project, headers, _, roles = proyecto
    ana = await make_user(email="ana@ejemplo.com")
    payload = {"user_id": str(ana.id), "project_role_id": roles["Colaborador"]["id"]}

    first = await client.post(
        f"/api/v1/projects/{project['id']}/members", json=payload, headers=headers
    )
    assert first.status_code == 201

    second = await client.post(
        f"/api/v1/projects/{project['id']}/members", json=payload, headers=headers
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_no_se_agregan_usuarios_desactivados(client, proyecto, make_user):
    project, headers, _, roles = proyecto
    inactivo = await make_user(email="inactivo@ejemplo.com", status=UserStatus.DISABLED)

    response = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(inactivo.id), "project_role_id": roles["Colaborador"]["id"]},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_no_se_puede_usar_un_rol_de_otro_proyecto(
    client, proyecto, make_user, make_project, auth_header
):
    """The composite foreign key would refuse it anyway; the service says so
    first, with a message that makes sense (RN-03)."""
    project, headers, _, _ = proyecto
    otra = await make_user(email="otra@ejemplo.com")
    ana = await make_user(email="ana@ejemplo.com")
    otro = await make_project(name="Visión por computador", leader_id=otra.id)
    otro_headers = await auth_header("otra@ejemplo.com", PASSWORD)
    roles_ajenos = await client.get(
        f"/api/v1/projects/{otro['id']}/roles", headers=otro_headers
    )
    rol_ajeno = next(r for r in roles_ajenos.json() if r["name"] == "Colaborador")

    response = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": rol_ajeno["id"]},
        headers=headers,
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retirar_a_un_miembro(client, proyecto, make_user):
    """RF-16: removing a member is not deleting their history."""
    project, headers, _, roles = proyecto
    ana = await make_user(email="ana@ejemplo.com")
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": roles["Colaborador"]["id"]},
        headers=headers,
    )

    response = await client.delete(
        f"/api/v1/projects/{project['id']}/members/{ana.id}", headers=headers
    )

    assert response.status_code == 204
    members = await client.get(f"/api/v1/projects/{project['id']}/members", headers=headers)
    assert {m["user"]["email"] for m in members.json()} == {"lider@ejemplo.com"}


@pytest.mark.asyncio
async def test_retirar_a_alguien_que_no_es_miembro(client, proyecto, make_user):
    project, headers, _, _ = proyecto
    ajena = await make_user(email="ajena@ejemplo.com")

    response = await client.delete(
        f"/api/v1/projects/{project['id']}/members/{ajena.id}", headers=headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_no_se_retira_al_ultimo_lider(client, proyecto):
    """RN-14: the project can never be left without anyone able to administer it."""
    project, headers, lider, _ = proyecto

    response = await client.delete(
        f"/api/v1/projects/{project['id']}/members/{lider.id}", headers=headers
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_PROJECT_ADMIN"


@pytest.mark.asyncio
async def test_se_retira_al_lider_si_hay_otro(client, proyecto, make_user):
    project, headers, lider, roles = proyecto
    segunda = await make_user(email="segunda@ejemplo.com")
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(segunda.id), "project_role_id": roles["Líder"]["id"]},
        headers=headers,
    )

    response = await client.delete(
        f"/api/v1/projects/{project['id']}/members/{lider.id}", headers=headers
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_cambiar_el_rol_de_un_miembro(client, proyecto, make_user):
    """RF-17: one role per project, replaced rather than accumulated."""
    project, headers, _, roles = proyecto
    ana = await make_user(email="ana@ejemplo.com")
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": roles["Observador"]["id"]},
        headers=headers,
    )

    response = await client.patch(
        f"/api/v1/projects/{project['id']}/members/{ana.id}/role",
        json={"project_role_id": roles["Colaborador"]["id"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["role"]["name"] == "Colaborador"

    members = await client.get(f"/api/v1/projects/{project['id']}/members", headers=headers)
    ana_row = next(m for m in members.json() if m["user"]["email"] == "ana@ejemplo.com")
    assert ana_row["role"]["name"] == "Colaborador"


@pytest.mark.asyncio
async def test_no_se_degrada_al_ultimo_lider(client, proyecto):
    """RN-14 again: the demotion of the last leader is the same hole as removing
    them."""
    project, headers, lider, roles = proyecto

    response = await client.patch(
        f"/api/v1/projects/{project['id']}/members/{lider.id}/role",
        json={"project_role_id": roles["Observador"]["id"]},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_PROJECT_ADMIN"


@pytest.mark.asyncio
async def test_el_unico_lider_puede_cambiar_a_otro_rol_que_administre(
    client, proyecto
):
    """Moving to a different role that still holds project.archive is fine: the
    project keeps an administrator."""
    project, headers, lider, _ = proyecto
    custom = await client.post(
        f"/api/v1/projects/{project['id']}/roles",
        json={
            "name": "Coordinador",
            "color": "#4B34E0",
            "permissions": ["task.view", "project.archive"],
        },
        headers=headers,
    )
    assert custom.status_code == 201

    response = await client.patch(
        f"/api/v1/projects/{project['id']}/members/{lider.id}/role",
        json={"project_role_id": custom.json()["id"]},
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["role"]["name"] == "Coordinador"


@pytest.mark.asyncio
async def test_no_se_le_quita_el_archivado_al_ultimo_rol_que_lo_tiene(
    client, proyecto
):
    """Editing a role can orphan a project just as surely as removing a member."""
    project, headers, lider, _ = proyecto
    # role.manage travels with the role, otherwise its own holder could not edit
    # it and the test would be measuring the wrong refusal.
    custom = (
        await client.post(
            f"/api/v1/projects/{project['id']}/roles",
            json={
                "name": "Coordinador",
                "color": "#4B34E0",
                "permissions": ["task.view", "project.archive", "role.manage"],
            },
            headers=headers,
        )
    ).json()
    moved = await client.patch(
        f"/api/v1/projects/{project['id']}/members/{lider.id}/role",
        json={"project_role_id": custom["id"]},
        headers=headers,
    )
    assert moved.status_code == 200, moved.text

    response = await client.patch(
        f"/api/v1/projects/{project['id']}/roles/{custom['id']}",
        json={
            "name": "Coordinador",
            "color": "#4B34E0",
            "permissions": ["task.view", "role.manage"],
        },
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_PROJECT_ADMIN"


@pytest.mark.asyncio
async def test_sin_member_add_no_se_agregan_miembros(
    client, proyecto, make_user, auth_header
):
    project, headers, _, roles = proyecto
    ana = await make_user(email="ana@ejemplo.com")
    beto = await make_user(email="beto@ejemplo.com")
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": roles["Colaborador"]["id"]},
        headers=headers,
    )
    ana_headers = await auth_header("ana@ejemplo.com", PASSWORD)

    response = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(beto.id), "project_role_id": roles["Observador"]["id"]},
        headers=ana_headers,
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_agregar_un_usuario_inexistente(client, proyecto):
    project, headers, _, roles = proyecto

    response = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={
            "user_id": str(uuid.uuid4()),
            "project_role_id": roles["Colaborador"]["id"],
        },
        headers=headers,
    )

    assert response.status_code == 404
