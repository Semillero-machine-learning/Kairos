"""Fixtures shared by the project integration tests.

Preconditions are arranged through the API rather than by inserting rows, so
every test starts from a project that was built the way production builds one:
three system roles and a leader, in a single transaction.
"""

import pytest_asyncio

from app.core.enums import GlobalRole

ADMIN_EMAIL = "admin@ejemplo.com"
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
