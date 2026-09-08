"""Notificaciones inmediatas: asignación y revisión (RF-39, RF-42, RN-25).

Es la mitad que a HU-09 le falta en test_hu09_revisar_entrega.py — "y quien
entregó recibe notificación y correo" — más el evento de asignación de HU-07.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.modules.notifications.models import Notification, NotificationDispatch

PASSWORD = "unaClaveLarga123"
ENTREGA = (
    "Entrené el modelo base con los datos de agosto. Exactitud del 0.87 en validación."
)
DEVOLUCION = "Falta la evaluación en el conjunto de prueba."


async def _avisos(db, user_id, kind) -> list[Notification]:
    rows = await db.execute(
        select(Notification).where(
            Notification.user_id == user_id, Notification.kind == kind
        )
    )
    return list(rows.scalars().all())


@pytest_asyncio.fixture
async def equipo(make_user, make_project, auth_header, add_member):
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana Gómez")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)

    return {
        "project": project,
        "carlos": carlos,
        "ana": ana,
        "lider": lider,
        "ana_headers": await auth_header("ana@ejemplo.com", PASSWORD),
    }


@pytest.mark.asyncio
async def test_asignacion_al_crear_la_tarea(db, equipo, make_task):
    """RF-39: el aviso lleva el título, el proyecto y la fecha límite."""
    task = await make_task(
        equipo["project"]["id"],
        equipo["lider"],
        title="Entrenar el modelo base",
        due_date="2026-10-01",
        assignee_ids=(equipo["ana"].id,),
    )

    avisos = await _avisos(db, equipo["ana"].id, "TASK_ASSIGNED")
    assert len(avisos) == 1
    assert "Entrenar el modelo base" in avisos[0].body
    assert str(avisos[0].task_id) == task["id"]
    assert str(avisos[0].project_id) == equipo["project"]["id"]


@pytest.mark.asyncio
async def test_asignacion_posterior(client, db, equipo, make_task):
    task = await make_task(equipo["project"]["id"], equipo["lider"])

    response = await client.post(
        f"/api/v1/tasks/{task['id']}/assignees",
        json={"user_id": str(equipo["ana"].id)},
        headers=equipo["lider"],
    )

    assert response.status_code == 200, response.text
    assert len(await _avisos(db, equipo["ana"].id, "TASK_ASSIGNED")) == 1


@pytest.mark.asyncio
async def test_reasignar_el_mismo_dia_vuelve_a_avisar(client, db, equipo, make_task):
    """Una asignación no es un recordatorio: no pasa por la tabla de despachos y
    por lo tanto la restricción de unicidad de RN-27 no la silencia."""
    task = await make_task(
        equipo["project"]["id"], equipo["lider"], assignee_ids=(equipo["ana"].id,)
    )
    quitado = await client.delete(
        f"/api/v1/tasks/{task['id']}/assignees/{equipo['ana'].id}",
        headers=equipo["lider"],
    )
    assert quitado.status_code == 200, quitado.text

    devuelto = await client.post(
        f"/api/v1/tasks/{task['id']}/assignees",
        json={"user_id": str(equipo["ana"].id)},
        headers=equipo["lider"],
    )

    assert devuelto.status_code == 200, devuelto.text
    assert len(await _avisos(db, equipo["ana"].id, "TASK_ASSIGNED")) == 2
    despachos = (await db.execute(select(NotificationDispatch))).scalars().all()
    assert list(despachos) == []


@pytest.mark.asyncio
async def test_entrega_aprobada_avisa_a_quien_entrego(
    client, db, equipo, make_task, move_task
):
    """El escenario "Aprobación" de HU-09, en su mitad de notificación."""
    task = await make_task(
        equipo["project"]["id"], equipo["lider"], assignee_ids=(equipo["ana"].id,)
    )
    await move_task(task["id"], "TODO", equipo["lider"])
    await move_task(task["id"], "IN_PROGRESS", equipo["ana_headers"])
    entrega = await client.post(
        f"/api/v1/tasks/{task['id']}/submissions",
        json={"description": ENTREGA},
        headers=equipo["ana_headers"],
    )
    assert entrega.status_code == 201, entrega.text

    revision = await client.post(
        f"/api/v1/submissions/{entrega.json()['id']}/review",
        json={"approved": True},
        headers=equipo["lider"],
    )

    assert revision.status_code == 200, revision.text
    avisos = await _avisos(db, equipo["ana"].id, "SUBMISSION_APPROVED")
    assert len(avisos) == 1
    assert "Carlos" in avisos[0].body
    # El revisor no se notifica a sí mismo.
    assert await _avisos(db, equipo["carlos"].id, "SUBMISSION_APPROVED") == []


@pytest.mark.asyncio
async def test_entrega_devuelta_avisa_con_el_comentario(
    client, db, equipo, make_task, move_task
):
    """El escenario "Devolución" de HU-09, en su mitad de notificación."""
    task = await make_task(
        equipo["project"]["id"], equipo["lider"], assignee_ids=(equipo["ana"].id,)
    )
    await move_task(task["id"], "TODO", equipo["lider"])
    await move_task(task["id"], "IN_PROGRESS", equipo["ana_headers"])
    entrega = await client.post(
        f"/api/v1/tasks/{task['id']}/submissions",
        json={"description": ENTREGA},
        headers=equipo["ana_headers"],
    )

    revision = await client.post(
        f"/api/v1/submissions/{entrega.json()['id']}/review",
        json={"approved": False, "comment": DEVOLUCION},
        headers=equipo["lider"],
    )

    assert revision.status_code == 200, revision.text
    avisos = await _avisos(db, equipo["ana"].id, "SUBMISSION_REJECTED")
    assert len(avisos) == 1
    assert "devolvió" in avisos[0].body


@pytest.mark.asyncio
async def test_un_fallo_de_correo_no_revierte_la_asignacion(
    client, db, equipo, make_task, monkeypatch
):
    """CLAUDE.md regla 9 y RN-30: el correo falla, la operación queda."""
    from app.integrations.email.client import EmailClient

    def _init(self) -> None:
        self._api_key = "re_test_key"
        self._sender = "Pruebas <pruebas@ejemplo.com>"
        self._backoff_base = 0

    async def _always_fail(self, **kwargs) -> str:
        raise RuntimeError("proveedor caído")

    monkeypatch.setattr(EmailClient, "__init__", _init)
    monkeypatch.setattr(EmailClient, "_deliver", _always_fail)

    task = await make_task(
        equipo["project"]["id"], equipo["lider"], assignee_ids=(equipo["ana"].id,)
    )

    # La tarea existe con su responsable...
    detalle = await client.get(f"/api/v1/tasks/{task['id']}", headers=equipo["lider"])
    assert detalle.status_code == 200
    assert [a["email"] for a in detalle.json()["assignees"]] == ["ana@ejemplo.com"]
    # ...y la notificación en la aplicación también, que es el canal que sí
    # controla la plataforma (RN-24).
    assert len(await _avisos(db, equipo["ana"].id, "TASK_ASSIGNED")) == 1
