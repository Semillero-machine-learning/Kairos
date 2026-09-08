"""HU-11 — Configurar los recordatorios (RF-43, RN-26).

Scenario names mirror docs/user-stories.md.
"""

import pytest

PASSWORD = "unaClaveLarga123"


@pytest.mark.asyncio
async def test_cambio_de_configuracion(client, admin_headers):
    # Dado que estoy autenticado como Administrador
    # Cuando cambio los días de aviso a [5, 2] y la hora de envío a las 8
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={"reminder_days_before": [5, 2], "send_hour": 8, "overdue_enabled": True},
        headers=admin_headers,
    )

    # Entonces la configuración queda guardada
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reminder_days_before"] == [5, 2]
    assert body["send_hour"] == 8
    # Y aplica a todos los proyectos por igual: la fila es única (RF-43), de modo
    # que leerla de nuevo devuelve exactamente lo mismo.
    releida = await client.get(
        "/api/v1/admin/notification-settings", headers=admin_headers
    )
    assert releida.json()["reminder_days_before"] == [5, 2]
    assert releida.json()["timezone"] == "America/Bogota"


@pytest.mark.asyncio
async def test_un_lider_intenta_configurar(
    client, make_user, make_project, auth_header
):
    # Dado que soy líder de un proyecto pero mi rol global es "MEMBER"
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)

    # Cuando intento modificar la configuración de notificaciones
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={"reminder_days_before": [1], "send_hour": 9, "overdue_enabled": False},
        headers=lider,
    )

    # Entonces recibo un error 403
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_un_lider_tampoco_la_puede_leer(
    client, make_user, make_project, auth_header
):
    """La lectura pide lo mismo que la escritura (api-contract.md 7)."""
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)

    response = await client.get(
        "/api/v1/admin/notification-settings", headers=lider
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_valores_invalidos(client, admin_headers):
    # Cuando envío una hora de envío de 25
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={"reminder_days_before": [3], "send_hour": 25, "overdue_enabled": True},
        headers=admin_headers,
    )

    # Entonces recibo un error de validación
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_demasiados_dias_de_aviso(client, admin_headers):
    """Máximo cinco valores (api-contract.md 7)."""
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={
            "reminder_days_before": [10, 7, 5, 3, 1, 0],
            "send_hour": 7,
            "overdue_enabled": True,
        },
        headers=admin_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_dias_de_aviso_repetidos(client, admin_headers):
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={"reminder_days_before": [3, 3], "send_hour": 7, "overdue_enabled": True},
        headers=admin_headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_dia_de_aviso_fuera_de_rango(client, admin_headers):
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={"reminder_days_before": [45], "send_hour": 7, "overdue_enabled": True},
        headers=admin_headers,
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_la_zona_horaria_no_se_puede_cambiar(client, admin_headers):
    """RN-26 la fija: aunque llegue en el cuerpo, se ignora."""
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={
            "reminder_days_before": [1],
            "send_hour": 7,
            "overdue_enabled": True,
            "timezone": "UTC",
        },
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["timezone"] == "America/Bogota"


@pytest.mark.asyncio
async def test_sin_dias_de_aviso(client, admin_headers):
    """Una lista vacía es válida: apaga los avisos previos sin tocar los de
    vencidas, que tienen su propio interruptor."""
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={"reminder_days_before": [], "send_hour": 7, "overdue_enabled": True},
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["reminder_days_before"] == []


@pytest.mark.asyncio
async def test_queda_registrado_quien_la_cambio(client, admin_headers, admin):
    response = await client.put(
        "/api/v1/admin/notification-settings",
        json={"reminder_days_before": [2], "send_hour": 6, "overdue_enabled": True},
        headers=admin_headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["updated_by"] == str(admin.id)
