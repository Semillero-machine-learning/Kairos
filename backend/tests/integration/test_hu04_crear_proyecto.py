"""HU-04 — Crear un proyecto (RF-13, RF-14, RN-13).

Scenario names mirror docs/user-stories.md so a failure points straight at the
acceptance criterion it broke.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.enums import GlobalRole, UserStatus
from app.modules.projects.constants import PERMISSION_CODES
from app.modules.projects.models import ProjectMember, ProjectRole

PASSWORD = "unaClaveLarga123"


@pytest.mark.asyncio
async def test_creacion_exitosa(client, db, admin_headers, make_user, get_roles):
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")

    response = await client.post(
        "/api/v1/projects",
        json={
            "name": "Detección de anomalías",
            "description": "Modelos de detección sobre series de tiempo.",
            "start_date": "2026-09-10",
            "leader_user_id": str(carlos.id),
        },
        headers=admin_headers,
    )

    assert response.status_code == 201, response.text
    project = response.json()
    # El proyecto queda en estado "ACTIVE"
    assert project["status"] == "ACTIVE"
    assert project["archived_at"] is None
    assert project["member_count"] == 1

    roles = (
        await db.execute(
            select(ProjectRole).where(ProjectRole.project_id == project["id"])
        )
    ).scalars().all()

    # Existen tres roles de proyecto: "Líder", "Colaborador" y "Observador"
    assert {role.name for role in roles} == {"Líder", "Colaborador", "Observador"}
    # Y los tres están marcados como roles del sistema
    assert all(role.is_system for role in roles)

    leader_role = next(role for role in roles if role.name == "Líder")
    # Y el rol "Líder" tiene los 14 permisos del catálogo
    assert leader_role.permission_codes == set(PERMISSION_CODES)
    assert len(leader_role.permission_codes) == 14

    member = (
        await db.execute(
            select(ProjectMember).where(ProjectMember.project_id == project["id"])
        )
    ).scalar_one()
    # Y "Carlos" es miembro con el rol "Líder"
    assert member.user_id == carlos.id
    assert member.project_role_id == leader_role.id


@pytest.mark.asyncio
async def test_un_lider_de_otro_proyecto_intenta_crear_uno_nuevo(
    client, admin_headers, make_user, auth_header, make_project
):
    # Dado que soy líder del proyecto "Visión por computador" con rol global "MEMBER"
    lider = await make_user(email="lider@ejemplo.com", full_name="Lider Ajeno")
    await make_project(name="Visión por computador", leader_id=lider.id)
    headers = await auth_header("lider@ejemplo.com", PASSWORD)

    # Cuando intento crear un proyecto
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Proyecto nuevo", "leader_user_id": str(lider.id)},
        headers=headers,
    )

    # Entonces recibo un error 403
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_el_lider_designado_debe_existir(client, admin_headers):
    response = await client.post(
        "/api/v1/projects",
        json={"name": "Proyecto sin líder", "leader_user_id": str(uuid.uuid4())},
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_el_lider_designado_debe_estar_activo(client, admin_headers, make_user):
    inactivo = await make_user(email="inactivo@ejemplo.com", status=UserStatus.DISABLED)

    response = await client.post(
        "/api/v1/projects",
        json={"name": "Proyecto sin líder activo", "leader_user_id": str(inactivo.id)},
        headers=admin_headers,
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_el_editor_de_lecciones_tampoco_crea_proyectos(
    client, make_user, auth_header
):
    """RN-01: no global role other than ADMIN opens this door."""
    await make_user(
        email="editor@ejemplo.com", global_role=GlobalRole.LESSON_EDITOR
    )
    headers = await auth_header("editor@ejemplo.com", PASSWORD)

    response = await client.post(
        "/api/v1/projects",
        json={"name": "Proyecto del editor", "leader_user_id": str(uuid.uuid4())},
        headers=headers,
    )
    assert response.status_code == 403
