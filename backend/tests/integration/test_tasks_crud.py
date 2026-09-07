"""Edición, borrado lógico, filtros y aislamiento de las tareas.

RF-36 (filtros y tablero), RF-37 (borrado lógico), RN-01 (el ADMIN global lee
pero no trabaja), RN-15 (proyecto archivado de solo lectura).
"""

import datetime

import pytest
import pytest_asyncio

from app.core.clock import today_in_bogota

PASSWORD = "unaClaveLarga123"


@pytest_asyncio.fixture
async def proyecto(make_user, make_project, auth_header, add_member):
    carlos = await make_user(email="carlos@ejemplo.com", full_name="Carlos")
    ana = await make_user(email="ana@ejemplo.com", full_name="Ana")
    project = await make_project(name="Detección de anomalías", leader_id=carlos.id)
    lider = await auth_header("carlos@ejemplo.com", PASSWORD)
    await add_member(project["id"], ana.id, "Colaborador", lider)
    return {
        "id": project["id"],
        "lider": lider,
        "ana_id": ana.id,
        "ana": await auth_header("ana@ejemplo.com", PASSWORD),
    }


@pytest.mark.asyncio
async def test_editar_una_tarea(client, proyecto, make_task):
    task = await make_task(proyecto["id"], proyecto["lider"], description="Original.")

    response = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"title": "Entrenar el modelo con datos nuevos", "periodicity": "MONTHLY"},
        headers=proyecto["lider"],
    )

    assert response.status_code == 200, response.text
    edited = response.json()
    assert edited["title"] == "Entrenar el modelo con datos nuevos"
    assert edited["periodicity"] == "MONTHLY"
    # Un PATCH no borra lo que no trae.
    assert edited["description"] == "Original."


@pytest.mark.asyncio
async def test_sin_el_permiso_de_editar_no_se_edita(client, proyecto, make_task):
    task = await make_task(proyecto["id"], proyecto["lider"])

    response = await client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={"title": "Otro título cualquiera"},
        headers=proyecto["ana"],
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_el_borrado_es_logico(client, proyecto, make_task):
    task = await make_task(proyecto["id"], proyecto["lider"])

    deleted = await client.delete(f"/api/v1/tasks/{task['id']}", headers=proyecto["lider"])
    assert deleted.status_code == 204, deleted.text

    # Desaparece de la API...
    gone = await client.get(f"/api/v1/tasks/{task['id']}", headers=proyecto["lider"])
    assert gone.status_code == 404
    listed = await client.get(
        f"/api/v1/projects/{proyecto['id']}/tasks", headers=proyecto["lider"]
    )
    assert listed.json()["total"] == 0

    # ...y de los conteos del tablero, que se calculan sobre lo mismo.
    detail = await client.get(f"/api/v1/projects/{proyecto['id']}", headers=proyecto["lider"])
    assert detail.json()["task_counts"]["BACKLOG"] == 0


@pytest.mark.asyncio
async def test_los_conteos_del_tablero_reflejan_los_estados(
    client, proyecto, make_task, move_task
):
    primera = await make_task(proyecto["id"], proyecto["lider"], title="Primera tarea")
    await make_task(proyecto["id"], proyecto["lider"], title="Segunda tarea")
    await move_task(primera["id"], "TODO", proyecto["lider"])

    response = await client.get(f"/api/v1/projects/{proyecto['id']}", headers=proyecto["lider"])

    assert response.status_code == 200, response.text
    assert response.json()["task_counts"] == {
        "BACKLOG": 1,
        "TODO": 1,
        "IN_PROGRESS": 0,
        "IN_REVIEW": 0,
        "DONE": 0,
    }


@pytest.mark.asyncio
async def test_filtros_del_tablero(client, proyecto, make_task, move_task):
    hoy = today_in_bogota()
    vencida = await make_task(
        proyecto["id"],
        proyecto["lider"],
        title="Tarea vencida",
        due_date=str(hoy - datetime.timedelta(days=1)),
        assignee_ids=(proyecto["ana_id"],),
    )
    await make_task(
        proyecto["id"],
        proyecto["lider"],
        title="Tarea futura",
        periodicity="WEEKLY",
        due_date=str(hoy + datetime.timedelta(days=7)),
    )
    await make_task(proyecto["id"], proyecto["lider"], title="Tarea sin fecha")
    await move_task(vencida["id"], "TODO", proyecto["lider"])

    async def titulos(query: str) -> list[str]:
        response = await client.get(
            f"/api/v1/projects/{proyecto['id']}/tasks?{query}", headers=proyecto["lider"]
        )
        assert response.status_code == 200, response.text
        return [task["title"] for task in response.json()["items"]]

    assert await titulos("status=TODO") == ["Tarea vencida"]
    assert await titulos(f"assignee_id={proyecto['ana_id']}") == ["Tarea vencida"]
    assert await titulos("periodicity=WEEKLY") == ["Tarea futura"]
    # Vencida es due_date < hoy y sin terminar; lo de hoy todavía no lo está.
    assert await titulos("overdue=true") == ["Tarea vencida"]
    assert len(await titulos("")) == 3


@pytest.mark.asyncio
async def test_una_tarea_de_otro_proyecto_no_existe(
    client, proyecto, make_user, make_project, auth_header, make_task
):
    # 404 y no 403: un 403 confirmaría que la tarea existe.
    task = await make_task(proyecto["id"], proyecto["lider"])
    otra = await make_user(email="otra@ejemplo.com")
    await make_project(name="Visión por computador", leader_id=otra.id)

    response = await client.get(
        f"/api/v1/tasks/{task['id']}",
        headers=await auth_header("otra@ejemplo.com", PASSWORD),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_el_admin_global_lee_el_tablero_pero_no_crea(
    client, proyecto, admin_headers, make_task
):
    # RN-01: lectura universal para supervisar, ningún permiso de trabajo.
    await make_task(proyecto["id"], proyecto["lider"], title="Entrenar el modelo")

    listed = await client.get(
        f"/api/v1/projects/{proyecto['id']}/tasks", headers=admin_headers
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    created = await client.post(
        f"/api/v1/projects/{proyecto['id']}/tasks",
        json={"title": "Una tarea del administrador"},
        headers=admin_headers,
    )
    assert created.status_code == 403


@pytest.mark.asyncio
async def test_un_proyecto_archivado_es_de_solo_lectura(
    client, proyecto, make_task, move_task
):
    # RN-15, EB-06. La comprobación está centralizada en la dependencia, así que
    # se verifica sobre las tres formas de escribir una tarea.
    task = await make_task(
        proyecto["id"], proyecto["lider"], assignee_ids=(proyecto["ana_id"],)
    )
    archived = await client.post(
        f"/api/v1/projects/{proyecto['id']}/archive", headers=proyecto["lider"]
    )
    assert archived.status_code == 200, archived.text

    creada = await client.post(
        f"/api/v1/projects/{proyecto['id']}/tasks",
        json={"title": "Una tarea nueva"},
        headers=proyecto["lider"],
    )
    assert creada.status_code == 409
    assert creada.json()["error"]["code"] == "PROJECT_ARCHIVED"

    movida = await move_task(task["id"], "TODO", proyecto["lider"])
    assert movida.status_code == 409
    assert movida.json()["error"]["code"] == "PROJECT_ARCHIVED"

    entregada = await client.post(
        f"/api/v1/tasks/{task['id']}/submissions",
        json={"description": "Un intento de entrega sobre un proyecto archivado."},
        headers=proyecto["ana"],
    )
    assert entregada.status_code == 409
    assert entregada.json()["error"]["code"] == "PROJECT_ARCHIVED"

    # Y sigue consultándose completo (RF-18).
    listed = await client.get(
        f"/api/v1/projects/{proyecto['id']}/tasks", headers=proyecto["ana"]
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


@pytest.mark.asyncio
async def test_el_titulo_se_valida(client, proyecto):
    response = await client.post(
        f"/api/v1/projects/{proyecto['id']}/tasks",
        json={"title": "  ab  "},
        headers=proyecto["lider"],
    )

    # Se recorta antes de medir, así que "  ab  " son dos caracteres, no seis.
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
