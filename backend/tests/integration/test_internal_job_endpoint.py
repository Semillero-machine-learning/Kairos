"""El endpoint interno del proceso programado (api-contract.md 9).

Es la única puerta de la aplicación que no usa JWT, así que su autenticación se
prueba aparte: un secreto compartido mal comprobado deja el disparador de todo el
sistema de notificaciones abierto a cualquiera.
"""

import pytest

from app.core.config import get_settings

RUTA = "/internal/jobs/reminders"


@pytest.fixture
def con_token(monkeypatch):
    """Fija un JOB_TOKEN conocido en los ajustes ya cacheados."""
    settings = get_settings()
    monkeypatch.setattr(settings, "job_token", "un-secreto-de-pruebas", raising=False)
    return "un-secreto-de-pruebas"


@pytest.mark.asyncio
async def test_sin_token(client, con_token):
    response = await client.post(RUTA)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.asyncio
async def test_token_incorrecto(client, con_token):
    response = await client.post(RUTA, headers={"X-Job-Token": "otro-secreto"})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_token_correcto_ejecuta_el_proceso(client, con_token):
    response = await client.post(RUTA, headers={"X-Job-Token": con_token})

    assert response.status_code == 200, response.text
    cuerpo = response.json()
    assert cuerpo["executed_at"] is not None
    assert cuerpo["due_soon_sent"] == 0
    assert cuerpo["overdue_sent"] == 0
    assert cuerpo["skipped_duplicates"] == 0
    assert cuerpo["failures"] == 0


@pytest.mark.asyncio
async def test_un_jwt_de_administrador_no_sirve(client, admin_headers, con_token):
    """El endpoint es para el disparador, no para personas."""
    response = await client.post(RUTA, headers=admin_headers)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sin_secreto_configurado_queda_cerrado(client, monkeypatch):
    """Un JOB_TOKEN vacío cierra la puerta, no la abre.

    Es la diferencia entre un despliegue nuevo sin configurar y un endpoint
    interno público.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "job_token", "", raising=False)

    response = await client.post(RUTA, headers={"X-Job-Token": ""})

    assert response.status_code == 401
