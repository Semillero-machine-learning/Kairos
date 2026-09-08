"""HU-10 — Recibir recordatorios de vencimiento (RF-40, RF-41, RF-44, RN-27, RN-28).

Scenario names mirror docs/user-stories.md. The job is called directly instead of
through the endpoint so that "today" can be injected: placing a task three days
out and waiting three days is not a test.

The mandatory coverage of CLAUDE.md §Pruebas item 3 — running the job twice must
not duplicate anything — is ``test_idempotencia``.
"""

import datetime

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.integrations.email.client import EmailClient
from app.jobs.reminders import run_reminders
from app.modules.notifications.models import Notification, NotificationDispatch

PASSWORD = "unaClaveLarga123"
# A fixed day, so the test does not depend on when it runs.
HOY = datetime.date(2026, 6, 15)


async def _notifications_of(db, user_id, kind=None) -> list[Notification]:
    query = select(Notification).where(Notification.user_id == user_id)
    if kind is not None:
        query = query.where(Notification.kind == kind)
    return list((await db.execute(query.order_by(Notification.created_at))).scalars().all())


async def _dispatch_count(db) -> int:
    return (
        await db.execute(select(func.count()).select_from(NotificationDispatch))
    ).scalar_one()


@pytest_asyncio.fixture
async def equipo(make_user, make_project, auth_header, add_member):
    """Carlos lidera (tiene "task.review"), Ana y Luis colaboran."""
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    luis = await make_user(email="luis@ejemplo.com", full_name="Luis Pérez")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)

    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)
    await add_member(project["id"], luis.id, "Colaborador", lider)

    return {
        "project": project,
        "carlos": carlos,
        "ana": ana,
        "luis": luis,
        "lider": lider,
        "ana_headers": await auth_header("ana@ejemplo.com", PASSWORD),
    }


@pytest_asyncio.fixture
async def limpia_notificaciones(db):
    """Borra lo que dejó la creación de la tarea.

    Asignar a alguien ya notifica (RF-39), y esas filas ensuciarían el conteo de
    los escenarios de esta historia, que son sobre el proceso programado.
    """

    async def _limpiar() -> None:
        await db.execute(Notification.__table__.delete())
        await db.commit()

    return _limpiar


@pytest.mark.asyncio
async def test_aviso_previo(db, equipo, make_task, move_task, limpia_notificaciones):
    # Dado que la configuración global tiene los días de aviso [3, 1, 0]
    # (es el valor por defecto de la migración 0003)
    # Y existe una tarea en "IN_PROGRESS" que vence en 3 días
    task = await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=(HOY + datetime.timedelta(days=3)).isoformat(),
        assignee_ids=(equipo["ana"].id, equipo["luis"].id),
    )
    assert (await move_task(task["id"], "TODO", equipo["lider"])).status_code == 200
    assert (
        await move_task(task["id"], "IN_PROGRESS", equipo["ana_headers"])
    ).status_code == 200
    await limpia_notificaciones()

    # Cuando se ejecuta el proceso programado
    resumen = await run_reminders(db, today=HOY)

    # Entonces cada responsable activo recibe notificación y correo
    assert resumen.due_soon_sent == 2
    assert resumen.failures == 0
    for persona in (equipo["ana"], equipo["luis"]):
        avisos = await _notifications_of(db, persona.id, "TASK_DUE_SOON")
        assert len(avisos) == 1
        assert "vence" in avisos[0].body
        assert str(avisos[0].task_id) == task["id"]
    # Y se registra el despacho con la fecha de hoy
    despachos = list((await db.execute(select(NotificationDispatch))).scalars().all())
    assert len(despachos) == 2
    assert {d.target_date for d in despachos} == {HOY}
    assert {d.status.value for d in despachos} == {"SENT"}


@pytest.mark.asyncio
async def test_idempotencia(db, equipo, make_task, limpia_notificaciones):
    # Dado que el proceso ya se ejecutó hoy y envió los avisos
    await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=(HOY + datetime.timedelta(days=1)).isoformat(),
        assignee_ids=(equipo["ana"].id,),
    )
    await limpia_notificaciones()
    primera = await run_reminders(db, today=HOY)
    assert primera.due_soon_sent == 1
    assert primera.skipped_duplicates == 0

    # Cuando se ejecuta de nuevo el mismo día
    segunda = await run_reminders(db, today=HOY)

    # Entonces no se envía ningún correo duplicado
    assert segunda.due_soon_sent == 0
    assert len(await _notifications_of(db, equipo["ana"].id, "TASK_DUE_SOON")) == 1
    assert await _dispatch_count(db) == 1
    # Y el resumen reporta los despachos omitidos
    assert segunda.skipped_duplicates == 1


@pytest.mark.asyncio
async def test_tarea_vencida(db, equipo, make_task, limpia_notificaciones):
    # Dado que una tarea venció ayer y no está en "DONE"
    # Y los avisos de vencidas están habilitados (valor por defecto)
    task = await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=(HOY - datetime.timedelta(days=1)).isoformat(),
        assignee_ids=(equipo["ana"].id,),
    )
    await limpia_notificaciones()

    # Cuando se ejecuta el proceso
    resumen = await run_reminders(db, today=HOY)

    # Entonces los responsables reciben el aviso
    assert len(await _notifications_of(db, equipo["ana"].id, "TASK_OVERDUE")) == 1
    # Y también lo reciben los miembros con el permiso "task.review"
    avisos_lider = await _notifications_of(db, equipo["carlos"].id, "TASK_OVERDUE")
    assert len(avisos_lider) == 1
    assert str(avisos_lider[0].task_id) == task["id"]
    # Luis colabora: ni es responsable ni puede revisar.
    assert await _notifications_of(db, equipo["luis"].id, "TASK_OVERDUE") == []
    assert resumen.overdue_sent == 2


@pytest.mark.asyncio
async def test_tarea_vencida_sin_responsables(db, equipo, make_task, limpia_notificaciones):
    # Dado que una tarea vencida no tiene responsables
    await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=(HOY - datetime.timedelta(days=2)).isoformat(),
    )
    await limpia_notificaciones()

    # Cuando se ejecuta el proceso
    resumen = await run_reminders(db, today=HOY)

    # Entonces solo se notifica a quienes tienen "task.review"
    assert resumen.overdue_sent == 1
    assert len(await _notifications_of(db, equipo["carlos"].id, "TASK_OVERDUE")) == 1
    assert await _notifications_of(db, equipo["ana"].id, "TASK_OVERDUE") == []


@pytest.mark.asyncio
async def test_proyecto_archivado(
    client, db, equipo, make_task, limpia_notificaciones
):
    # Dado que el proyecto de la tarea está archivado
    await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=(HOY - datetime.timedelta(days=1)).isoformat(),
        assignee_ids=(equipo["ana"].id,),
    )
    archivado = await client.post(
        f"/api/v1/projects/{equipo['project']['id']}/archive", headers=equipo["lider"]
    )
    assert archivado.status_code == 200, archivado.text
    await limpia_notificaciones()

    # Cuando se ejecuta el proceso
    resumen = await run_reminders(db, today=HOY)

    # Entonces no se envía ninguna notificación de esa tarea (RN-16)
    assert resumen.overdue_sent == 0
    assert resumen.due_soon_sent == 0
    assert await _dispatch_count(db) == 0


@pytest.mark.asyncio
async def test_usuario_desactivado(
    client, db, equipo, admin_headers, make_task, limpia_notificaciones
):
    # Dado que un responsable está desactivado
    task = await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=(HOY + datetime.timedelta(days=3)).isoformat(),
        assignee_ids=(equipo["ana"].id, equipo["luis"].id),
    )
    desactivado = await client.patch(
        f"/api/v1/users/{equipo['ana'].id}/status",
        json={"status": "DISABLED"},
        headers=admin_headers,
    )
    assert desactivado.status_code == 200, desactivado.text
    await limpia_notificaciones()

    # Cuando se ejecuta el proceso
    resumen = await run_reminders(db, today=HOY)

    # Entonces no recibe ninguna notificación (RF-45)
    assert await _notifications_of(db, equipo["ana"].id) == []
    # Y quien sigue activo sí la recibe: la tarea no se cae entera.
    assert len(await _notifications_of(db, equipo["luis"].id, "TASK_DUE_SOON")) == 1
    assert resumen.due_soon_sent == 1
    assert task["id"] is not None


@pytest.mark.asyncio
async def test_fallo_del_proveedor_de_correo(
    db, equipo, make_task, limpia_notificaciones, monkeypatch
):
    await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=HOY.isoformat(),
        assignee_ids=(equipo["ana"].id,),
    )
    await limpia_notificaciones()

    # Dado que Resend devuelve un error.
    # El parche se aplica después de crear la tarea: asignar a alguien ya manda
    # un correo (RF-39), y contarlo aquí mediría dos envíos en vez de uno.
    intentos = {"count": 0}

    def _init(self) -> None:
        self._api_key = "re_test_key"
        self._sender = "Pruebas <pruebas@ejemplo.com>"
        self._backoff_base = 0  # sin esperas reales

    async def _always_fail(self, **kwargs) -> str:
        intentos["count"] += 1
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr(EmailClient, "__init__", _init)
    monkeypatch.setattr(EmailClient, "_deliver", _always_fail)

    # Cuando se intenta el envío
    resumen = await run_reminders(db, today=HOY)

    # Entonces se reintenta hasta 3 veces
    assert intentos["count"] == 3
    # Y la notificación dentro de la aplicación se crea de todos modos (RN-24)
    assert len(await _notifications_of(db, equipo["ana"].id, "TASK_DUE_SOON")) == 1
    # Y el despacho queda registrado como fallido
    despacho = (
        await db.execute(select(NotificationDispatch))
    ).scalar_one()
    assert despacho.status.value == "FAILED"
    assert despacho.attempts == 3
    assert "proveedor caído" in despacho.error_message
    assert resumen.failures == 1


@pytest.mark.asyncio
async def test_tarea_terminada_no_genera_avisos(
    db, equipo, make_task, move_task, client, limpia_notificaciones
):
    """RN-28: una tarea en DONE ya no le importa a nadie."""
    task = await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=(HOY - datetime.timedelta(days=1)).isoformat(),
        assignee_ids=(equipo["ana"].id,),
    )
    assert (await move_task(task["id"], "TODO", equipo["lider"])).status_code == 200
    assert (
        await move_task(task["id"], "IN_PROGRESS", equipo["ana_headers"])
    ).status_code == 200
    entrega = await client.post(
        f"/api/v1/tasks/{task['id']}/submissions",
        json={"description": "Terminado, con las métricas del informe."},
        headers=equipo["ana_headers"],
    )
    assert entrega.status_code == 201, entrega.text
    revision = await client.post(
        f"/api/v1/submissions/{entrega.json()['id']}/review",
        json={"approved": True},
        headers=equipo["lider"],
    )
    assert revision.status_code == 200, revision.text
    await limpia_notificaciones()

    resumen = await run_reminders(db, today=HOY)

    assert resumen.overdue_sent == 0
    assert await _dispatch_count(db) == 0


@pytest.mark.asyncio
async def test_sin_fecha_limite_no_hay_recordatorio(
    db, equipo, make_task, limpia_notificaciones
):
    """Una tarea sin fecha no vence nunca: no hay nada contra qué comparar."""
    await make_task(
        equipo["project"]["id"], equipo["lider"], assignee_ids=(equipo["ana"].id,)
    )
    await limpia_notificaciones()

    resumen = await run_reminders(db, today=HOY)

    assert resumen.due_soon_sent == 0
    assert resumen.overdue_sent == 0


@pytest.mark.asyncio
async def test_avisos_de_vencidas_desactivados(
    client, db, equipo, admin_headers, make_task, limpia_notificaciones
):
    """El interruptor de RN-26 apaga solo los avisos de vencidas."""
    await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        due_date=(HOY - datetime.timedelta(days=1)).isoformat(),
        assignee_ids=(equipo["ana"].id,),
    )
    ajuste = await client.put(
        "/api/v1/admin/notification-settings",
        json={"reminder_days_before": [3, 1, 0], "send_hour": 7, "overdue_enabled": False},
        headers=admin_headers,
    )
    assert ajuste.status_code == 200, ajuste.text
    await limpia_notificaciones()

    resumen = await run_reminders(db, today=HOY)

    assert resumen.overdue_sent == 0
    assert await _dispatch_count(db) == 0
