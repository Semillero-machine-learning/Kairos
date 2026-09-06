"""Health probe: exercises the DB round-trip that keeps the service awake."""

import pytest


@pytest.mark.asyncio
async def test_health_ok(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
