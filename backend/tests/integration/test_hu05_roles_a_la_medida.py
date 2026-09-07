"""HU-05 — Crear un rol a la medida (RF-21 a RF-24, RN-05, RN-18 a RN-23)."""

import pytest
import pytest_asyncio

PASSWORD = "unaClaveLarga123"
REVISOR = {
    "name": "Revisor",
    "color": "#B8860B",
    "permissions": ["task.view", "task.comment", "task.review"],
}


@pytest_asyncio.fixture
async def proyecto(make_user, make_project, auth_header):
    """Dado que soy líder del proyecto "Detección de anomalías"."""
    lider = await make_user(email="lider@ejemplo.com", full_name="Lider Principal")
    project = await make_project(name="Detección de anomalías", leader_id=lider.id)
    headers = await auth_header("lider@ejemplo.com", PASSWORD)
    return project, headers, lider


@pytest.mark.asyncio
async def test_creacion_exitosa(client, proyecto, admin_headers, make_user, make_project):
    project, headers, lider = proyecto

    # Cuando creo el rol "Revisor" en color "#B8860B" con sus tres permisos
    response = await client.post(
        f"/api/v1/projects/{project['id']}/roles", json=REVISOR, headers=headers
    )

    assert response.status_code == 201, response.text
    role = response.json()
    # Entonces el rol queda creado dentro de ese proyecto
    assert role["project_id"] == project["id"]
    assert role["is_system"] is False
    assert sorted(role["permissions"]) == ["task.comment", "task.review", "task.view"]
    # Y queda registrado que yo lo creé y en qué fecha (RN-19)
    assert role["created_by"]["id"] == str(lider.id)
    assert role["created_by"]["full_name"] == "Lider Principal"
    assert role["created_at"] is not None

    # Y el rol no aparece en ningún otro proyecto (RF-23)
    otra = await make_user(email="otra@ejemplo.com")
    otro = await make_project(name="Visión por computador", leader_id=otra.id)
    roles_del_otro = await client.get(
        f"/api/v1/projects/{otro['id']}/roles", headers=admin_headers
    )
    assert "Revisor" not in {r["name"] for r in roles_del_otro.json()}


@pytest.mark.asyncio
async def test_rol_sin_el_permiso_de_ver(client, proyecto):
    project, headers, _ = proyecto

    # Cuando creo un rol con los permisos "task.review" y "task.comment" solamente
    response = await client.post(
        f"/api/v1/projects/{project['id']}/roles",
        json={
            "name": "Revisor ciego",
            "color": "#B8860B",
            "permissions": ["task.review", "task.comment"],
        },
        headers=headers,
    )

    # Entonces recibo un error de validación, y se me indica que task.view es obligatorio
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "task.view" in error["message"]
    assert error["details"] == {"missing": ["task.view"]}


@pytest.mark.asyncio
async def test_nombre_repetido(client, proyecto):
    project, headers, _ = proyecto
    # Dado que ya existe el rol "Revisor" en el proyecto
    first = await client.post(
        f"/api/v1/projects/{project['id']}/roles", json=REVISOR, headers=headers
    )
    assert first.status_code == 201

    # Cuando creo otro llamado "revisor"
    response = await client.post(
        f"/api/v1/projects/{project['id']}/roles",
        json={**REVISOR, "name": "revisor"},
        headers=headers,
    )

    # Entonces recibo un error 409 con el código "ROLE_NAME_TAKEN"
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ROLE_NAME_TAKEN"


@pytest.mark.asyncio
async def test_editar_un_rol_del_sistema(client, proyecto, get_roles):
    project, headers, _ = proyecto
    roles = await get_roles(project["id"], headers)

    # Cuando intento cambiar los permisos del rol "Líder"
    response = await client.patch(
        f"/api/v1/projects/{project['id']}/roles/{roles['Líder']['id']}",
        json={"name": "Líder", "color": "#1F6F5C", "permissions": ["task.view"]},
        headers=headers,
    )

    # Entonces recibo un error 409 con el código "SYSTEM_ROLE_IMMUTABLE"
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SYSTEM_ROLE_IMMUTABLE"


@pytest.mark.asyncio
async def test_borrar_un_rol_del_sistema(client, proyecto, get_roles):
    """RN-23 covers deletion as well as editing."""
    project, headers, _ = proyecto
    roles = await get_roles(project["id"], headers)

    response = await client.delete(
        f"/api/v1/projects/{project['id']}/roles/{roles['Observador']['id']}",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SYSTEM_ROLE_IMMUTABLE"


@pytest.mark.asyncio
async def test_borrar_un_rol_con_miembros(client, proyecto, make_user):
    project, headers, _ = proyecto
    role = (
        await client.post(
            f"/api/v1/projects/{project['id']}/roles", json=REVISOR, headers=headers
        )
    ).json()

    # Dado que el rol "Revisor" tiene 2 miembros asignados
    for email in ("ana@ejemplo.com", "beto@ejemplo.com"):
        user = await make_user(email=email)
        added = await client.post(
            f"/api/v1/projects/{project['id']}/members",
            json={"user_id": str(user.id), "project_role_id": role["id"]},
            headers=headers,
        )
        assert added.status_code == 201, added.text

    # Cuando intento eliminarlo
    response = await client.delete(
        f"/api/v1/projects/{project['id']}/roles/{role['id']}", headers=headers
    )

    # Entonces recibo un error 409 indicando que tiene 2 miembros asignados (EB-05)
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "ROLE_HAS_MEMBERS"
    assert "2" in error["message"]
    assert error["details"] == {"member_count": 2}


@pytest.mark.asyncio
async def test_borrar_un_rol_sin_miembros(client, proyecto):
    project, headers, _ = proyecto
    role = (
        await client.post(
            f"/api/v1/projects/{project['id']}/roles", json=REVISOR, headers=headers
        )
    ).json()

    response = await client.delete(
        f"/api/v1/projects/{project['id']}/roles/{role['id']}", headers=headers
    )

    assert response.status_code == 204
    roles = await client.get(f"/api/v1/projects/{project['id']}/roles", headers=headers)
    assert "Revisor" not in {r["name"] for r in roles.json()}


@pytest.mark.asyncio
async def test_el_cambio_de_permisos_aplica_de_inmediato(
    client, proyecto, make_user, auth_header
):
    """RN-22: the permission set is read per request, never from the JWT, so a
    role edit reaches an open session without a new sign-in."""
    project, headers, _ = proyecto
    role = (
        await client.post(
            f"/api/v1/projects/{project['id']}/roles", json=REVISOR, headers=headers
        )
    ).json()

    # Dado que "Ana" tiene el rol "Revisor" y una sesión abierta
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana")
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": role["id"]},
        headers=headers,
    )
    ana_headers = await auth_header("ana@ejemplo.com", PASSWORD)

    before = await client.get(f"/api/v1/projects/{project['id']}", headers=ana_headers)
    assert "task.review" in before.json()["my_permissions"]

    # Cuando le quito el permiso "task.review" al rol
    edited = await client.patch(
        f"/api/v1/projects/{project['id']}/roles/{role['id']}",
        json={
            "name": "Revisor",
            "color": "#B8860B",
            "permissions": ["task.view", "task.comment"],
        },
        headers=headers,
    )
    assert edited.status_code == 200, edited.text
    assert sorted(edited.json()["permissions"]) == ["task.comment", "task.view"]
    assert edited.json()["member_count"] == 1

    # Entonces la siguiente petición de Ana ya no ve ese permiso, con el mismo token
    after = await client.get(f"/api/v1/projects/{project['id']}", headers=ana_headers)
    assert "task.review" not in after.json()["my_permissions"]
    assert after.request.headers["authorization"] == before.request.headers["authorization"]


@pytest.mark.asyncio
async def test_un_permiso_inexistente_se_rechaza(client, proyecto):
    """The catalog is closed: no role can invent a permission (RN-06)."""
    project, headers, _ = proyecto

    response = await client.post(
        f"/api/v1/projects/{project['id']}/roles",
        json={
            "name": "Todopoderoso",
            "color": "#B8860B",
            "permissions": ["task.view", "task.rule_the_world"],
        },
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"] == {"unknown": ["task.rule_the_world"]}


@pytest.mark.asyncio
async def test_un_color_invalido_se_rechaza(client, proyecto):
    project, headers, _ = proyecto

    response = await client.post(
        f"/api/v1/projects/{project['id']}/roles",
        json={"name": "Revisor", "color": "rojo", "permissions": ["task.view"]},
        headers=headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sin_role_manage_no_se_crean_roles(
    client, proyecto, make_user, auth_header, get_roles
):
    """RN-18: creating roles needs role.manage, which only the leader holds by
    default."""
    project, headers, _ = proyecto
    roles = await get_roles(project["id"], headers)
    ana = await make_user(email="ana@ejemplo.com")
    await client.post(
        f"/api/v1/projects/{project['id']}/members",
        json={"user_id": str(ana.id), "project_role_id": roles["Colaborador"]["id"]},
        headers=headers,
    )
    ana_headers = await auth_header("ana@ejemplo.com", PASSWORD)

    response = await client.post(
        f"/api/v1/projects/{project['id']}/roles", json=REVISOR, headers=ana_headers
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_un_rol_de_otro_proyecto_no_se_puede_editar(
    client, proyecto, make_user, make_project, admin_headers
):
    """RN-03, RN-04: a role belongs to exactly one project, and the others cannot
    even see that it exists."""
    project, headers, _ = proyecto
    otra = await make_user(email="otra@ejemplo.com")
    otro = await make_project(name="Visión por computador", leader_id=otra.id)
    ajeno = (
        await client.post(
            f"/api/v1/projects/{otro['id']}/roles",
            json=REVISOR,
            headers=admin_headers,
        )
    )
    # The admin is not a member of the other project, so they cannot manage roles
    # there either: the role is created by its own leader.
    assert ajeno.status_code == 403

    response = await client.patch(
        f"/api/v1/projects/{project['id']}/roles/{otro['id']}",
        json=REVISOR,
        headers=headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_un_nombre_de_rol_de_solo_espacios_se_rechaza(client, proyecto):
    """«  A  » tiene cinco caracteres pero se guarda con uno: el recorte va antes
    de la validación de longitud, no después."""
    project, headers, _ = proyecto
    response = await client.post(
        f"/api/v1/projects/{project['id']}/roles",
        json={"name": "  A  ", "color": "#B8860B", "permissions": ["task.view"]},
        headers=headers,
    )
    assert response.status_code == 422
