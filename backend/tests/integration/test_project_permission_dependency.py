"""require_project_permission — cobertura obligatoria (CLAUDE.md, pruebas 2).

The four cases the guard has to get right, plus the archived project: a system
role, a custom role, someone who is not a member, and the global ADMIN. If any
of these regresses, every other authorization rule in the platform is worthless,
which is why they get a file of their own.
"""

import uuid

import pytest

from app.core.enums import UserStatus

PASSWORD = "unaClaveLarga123"


@pytest.mark.asyncio
async def test_rol_del_sistema_resuelve_los_catorce_permisos(
    client, make_user, make_project, auth_header
):
    lider = await make_user(email="lider@ejemplo.com", full_name="Lider")
    project = await make_project(name="Proyecto con líder", leader_id=lider.id)
    headers = await auth_header("lider@ejemplo.com", PASSWORD)

    response = await client.get(f"/api/v1/projects/{project['id']}", headers=headers)

    assert response.status_code == 200
    assert len(response.json()["my_permissions"]) == 14
    assert response.json()["my_role"]["name"] == "Líder"


@pytest.mark.asyncio
async def test_rol_a_la_medida_resuelve_solo_sus_permisos(
    client, make_user, make_project, auth_header, get_roles
):
    lider = await make_user(email="lider@ejemplo.com")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana")
    project = await make_project(name="Proyecto con revisor", leader_id=lider.id)
    leader_headers = await auth_header("lider@ejemplo.com", PASSWORD)

    created = await client.post(
        f"/api/v1/projects/{project['id']}/roles",
        json={
            "name": "Revisor",
            "color": "#B8860B",
            "permissions": ["task.view", "task.comment", "task.review"],
        },
        headers=leader_headers,
    )
    assert created.status_code == 201, created.text

    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": created.json()["id"]},
        headers=leader_headers,
    )

    ana_headers = await auth_header("ana@ejemplo.com", PASSWORD)
    detail = await client.get(f"/api/v1/projects/{project['id']}", headers=ana_headers)

    assert detail.status_code == 200
    assert detail.json()["my_permissions"] == ["task.comment", "task.review", "task.view"]

    # Reading is allowed; managing roles is not.
    denied = await client.post(
        f"/api/v1/projects/{project['id']}/roles",
        json={"name": "Otro", "color": "#123456", "permissions": ["task.view"]},
        headers=ana_headers,
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_no_miembro_recibe_404_no_403(
    client, make_user, make_project, auth_header
):
    """A 403 would confirm the project exists. It has to be a 404."""
    lider = await make_user(email="lider@ejemplo.com")
    await make_user(email="extranio@ejemplo.com")
    project = await make_project(name="Proyecto ajeno", leader_id=lider.id)
    headers = await auth_header("extranio@ejemplo.com", PASSWORD)

    response = await client.get(f"/api/v1/projects/{project['id']}", headers=headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    # Identical answer for a project that truly does not exist.
    missing = await client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=headers)
    assert missing.status_code == 404
    assert missing.json()["error"] == response.json()["error"]


@pytest.mark.asyncio
async def test_admin_global_lee_cualquier_proyecto_sin_ser_miembro(
    client, make_user, make_project, admin_headers
):
    """RN-01: universal read access, so an administrator can supervise."""
    lider = await make_user(email="lider@ejemplo.com")
    project = await make_project(name="Proyecto supervisado", leader_id=lider.id)

    response = await client.get(f"/api/v1/projects/{project['id']}", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["my_role"] is None
    assert "task.view" in response.json()["my_permissions"]


@pytest.mark.asyncio
async def test_admin_global_no_obtiene_permisos_de_trabajo(
    client, make_user, make_project, admin_headers
):
    """RN-01: the global role never grants task-level write access."""
    lider = await make_user(email="lider@ejemplo.com")
    project = await make_project(name="Proyecto supervisado", leader_id=lider.id)

    detail = await client.get(f"/api/v1/projects/{project['id']}", headers=admin_headers)
    permissions = set(detail.json()["my_permissions"])

    assert not permissions & {
        "task.create",
        "task.edit_any",
        "task.delete",
        "task.assign",
        "task.change_status_any",
        "task.review",
        "task.comment",
        "role.manage",
        "project.edit",
        "project.archive",
    }
    # Editing the project itself is refused, for the same reason.
    edit = await client.patch(
        f"/api/v1/projects/{project['id']}",
        json={"name": "Renombrado por el admin"},
        headers=admin_headers,
    )
    assert edit.status_code == 403


@pytest.mark.asyncio
async def test_admin_global_puede_reasignar_el_liderazgo(
    client, make_user, make_project, admin_headers, get_roles
):
    """RN-14: the administrator can always reassign leadership, which is the one
    write path a non-member ADMIN keeps."""
    lider = await make_user(email="lider@ejemplo.com")
    nueva = await make_user(email="nueva@ejemplo.com", full_name="Nueva Líder")
    project = await make_project(name="Proyecto huérfano", leader_id=lider.id)
    roles = await get_roles(project["id"], admin_headers)

    response = await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(nueva.id), "project_role_id": roles["Líder"]["id"]},
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["role"]["name"] == "Líder"


@pytest.mark.asyncio
async def test_proyecto_archivado_se_lee_pero_no_se_modifica(
    client, make_user, make_project, auth_header, get_roles
):
    """RN-15 with RF-18: read-only, not invisible."""
    lider = await make_user(email="lider@ejemplo.com")
    otra = await make_user(email="otra@ejemplo.com")
    project = await make_project(name="Proyecto archivado", leader_id=lider.id)
    headers = await auth_header("lider@ejemplo.com", PASSWORD)
    roles = await get_roles(project["id"], headers)

    archived = await client.post(
        f"/api/v1/projects/{project['id']}/archive", headers=headers
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    assert archived.json()["archived_at"] is not None

    # Reads keep working, in full.
    detail = await client.get(f"/api/v1/projects/{project['id']}", headers=headers)
    assert detail.status_code == 200
    members = await client.get(f"/api/v1/projects/{project['id']}/members", headers=headers)
    assert members.status_code == 200
    roles_response = await client.get(
        f"/api/v1/projects/{project['id']}/roles", headers=headers
    )
    assert roles_response.status_code == 200

    # Every write is refused with the same code (EB-06).
    for method, path, body in [
        ("patch", f"/api/v1/projects/{project['id']}", {"name": "Otro nombre"}),
        (
            "post",
            f"/api/v1/projects/{project['id']}/members",
            {"user_id": str(otra.id), "project_role_id": roles["Colaborador"]["id"]},
        ),
        (
            "post",
            f"/api/v1/projects/{project['id']}/roles",
            {"name": "Revisor", "color": "#B8860B", "permissions": ["task.view"]},
        ),
    ]:
        response = await getattr(client, method)(path, json=body, headers=headers)
        assert response.status_code == 409, (path, response.text)
        assert response.json()["error"]["code"] == "PROJECT_ARCHIVED"

    # Removing a member is refused too, even though it carries no body.
    removal = await client.delete(
        f"/api/v1/projects/{project['id']}/members/{lider.id}", headers=headers
    )
    assert removal.status_code == 409
    assert removal.json()["error"]["code"] == "PROJECT_ARCHIVED"

    # Unarchiving is the one write that gets through (RN-15).
    restored = await client.post(
        f"/api/v1/projects/{project['id']}/unarchive", headers=headers
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "ACTIVE"
    assert restored.json()["archived_at"] is None


@pytest.mark.asyncio
async def test_un_usuario_desactivado_no_resuelve_ningun_permiso(
    client, db, make_user, make_project, auth_header
):
    """RN-44: the session dies with the account, before any project lookup."""
    lider = await make_user(email="lider@ejemplo.com")
    project = await make_project(name="Proyecto activo", leader_id=lider.id)
    headers = await auth_header("lider@ejemplo.com", PASSWORD)

    lider.status = UserStatus.DISABLED
    await db.flush()

    response = await client.get(f"/api/v1/projects/{project['id']}", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sin_token_no_hay_proyecto(client, make_user, make_project):
    lider = await make_user(email="lider@ejemplo.com")
    project = await make_project(name="Proyecto privado", leader_id=lider.id)

    response = await client.get(f"/api/v1/projects/{project['id']}")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"
