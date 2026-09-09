"""Fixtures shared by the project integration tests.

Preconditions are arranged through the API rather than by inserting rows, so
every test starts from a project that was built the way production builds one:
three system roles and a leader, in a single transaction.
"""

import pytest_asyncio

from app.core.enums import GlobalRole

ADMIN_EMAIL = "admin@ejemplo.com"
EDITOR_EMAIL = "editora@ejemplo.com"
MEMBER_EMAIL = "miembro@ejemplo.com"
PASSWORD = "unaClaveLarga123"


@pytest_asyncio.fixture
async def admin(make_user):
    """The platform administrator: the only one who can create projects (RN-13)."""
    return await make_user(
        email=ADMIN_EMAIL,
        full_name="Admina Principal",
        password=PASSWORD,
        global_role=GlobalRole.ADMIN,
    )


@pytest_asyncio.fixture
async def admin_headers(admin, auth_header):
    return await auth_header(ADMIN_EMAIL, PASSWORD)


@pytest_asyncio.fixture
async def lesson_editor(make_user):
    """El rol global que manda en el catálogo, sin nada más (RN-31)."""
    return await make_user(
        email=EDITOR_EMAIL,
        full_name="Edita Lecciones",
        password=PASSWORD,
        global_role=GlobalRole.LESSON_EDITOR,
    )


@pytest_asyncio.fixture
async def editor_headers(lesson_editor, auth_header):
    return await auth_header(EDITOR_EMAIL, PASSWORD)


@pytest_asyncio.fixture
async def plain_member(make_user):
    """Rol global MEMBER: el resto del semillero."""
    return await make_user(
        email=MEMBER_EMAIL,
        full_name="Miembro Común",
        password=PASSWORD,
        global_role=GlobalRole.MEMBER,
    )


@pytest_asyncio.fixture
async def member_headers(plain_member, auth_header):
    return await auth_header(MEMBER_EMAIL, PASSWORD)


@pytest_asyncio.fixture
def make_module(client):
    """Crea un módulo por la API y, si se pide, lo publica.

    Publicar es un segundo llamado a propósito: el módulo nace en borrador
    (RF-49) y ninguna prueba debería poder saltarse ese hecho.
    """

    async def _make(
        *,
        title: str,
        headers: dict[str, str],
        description: str | None = None,
        published: bool = False,
    ) -> dict:
        response = await client.post(
            "/api/v1/lesson-modules",
            json={"title": title, "description": description},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        module = response.json()
        if published:
            published_response = await client.post(
                f"/api/v1/lesson-modules/{module['id']}/publish",
                json={"published": True},
                headers=headers,
            )
            assert published_response.status_code == 200, published_response.text
            module = published_response.json()
        return module

    return _make


@pytest_asyncio.fixture
def make_project(client, admin_headers):
    """Create a project through POST /projects, with the given leader."""

    async def _make(*, name: str, leader_id, description: str | None = None) -> dict:
        response = await client.post(
            "/api/v1/projects",
            json={
                "name": name,
                "description": description,
                "leader_user_id": str(leader_id),
            },
            headers=admin_headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest_asyncio.fixture
def get_roles(client):
    """The project's roles, keyed by name, as the leader sees them."""

    async def _get(project_id: str, headers: dict[str, str]) -> dict[str, dict]:
        response = await client.get(f"/api/v1/projects/{project_id}/roles", headers=headers)
        assert response.status_code == 200, response.text
        return {role["name"]: role for role in response.json()}

    return _get


@pytest_asyncio.fixture
def add_member(client, get_roles):
    """Add somebody to a project with one of its roles, by role name."""

    async def _add(
        project_id: str, user_id, role_name: str, headers: dict[str, str]
    ) -> dict:
        roles = await get_roles(project_id, headers)
        assert role_name in roles, f"el proyecto no tiene el rol {role_name}"
        response = await client.post(
            f"/api/v1/projects/{project_id}/members",
            json={"user_id": str(user_id), "project_role_id": roles[role_name]["id"]},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _add


@pytest_asyncio.fixture
def make_task(client):
    """Create a task through the API, so it starts where production starts it."""

    async def _make(
        project_id: str,
        headers: dict[str, str],
        *,
        title: str = "Entrenar el modelo base",
        description: str | None = None,
        periodicity: str = "ONE_TIME",
        due_date: str | None = None,
        assignee_ids: tuple = (),
    ) -> dict:
        response = await client.post(
            f"/api/v1/projects/{project_id}/tasks",
            json={
                "title": title,
                "description": description,
                "periodicity": periodicity,
                "due_date": due_date,
                "assignee_ids": [str(user_id) for user_id in assignee_ids],
            },
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest_asyncio.fixture
def move_task(client):
    """Walk a task through the state machine, one legal step at a time."""

    async def _move(task_id: str, target: str, headers: dict[str, str]):
        return await client.post(
            f"/api/v1/tasks/{task_id}/status", json={"status": target}, headers=headers
        )

    return _move
