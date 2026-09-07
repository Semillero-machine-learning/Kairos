"""Transiciones de estado de tareas — cobertura obligatoria (CLAUDE.md, pruebas 1).

Every valid and invalid transition of the table in business-rules.md 4. The
table is transcribed here a second time, by hand, from the document rather than
from the code: two independent copies that have to agree is the whole point. If
someone edits state_machine.py without editing business-rules.md, this file is
what notices.
"""

import itertools

import pytest

from app.core.enums import TaskStatus
from app.modules.tasks import state_machine
from app.modules.tasks.state_machine import CHANGE_STATUS_ANY, REVIEW

B, T, P, R, D = (
    TaskStatus.BACKLOG,
    TaskStatus.TODO,
    TaskStatus.IN_PROGRESS,
    TaskStatus.IN_REVIEW,
    TaskStatus.DONE,
)

# business-rules.md 4: (desde, hacia, quién, exige entrega, sale por revisión)
TABLA = [
    (B, T, CHANGE_STATUS_ANY, False, False, False),
    (T, P, CHANGE_STATUS_ANY, True, False, False),
    (T, B, CHANGE_STATUS_ANY, False, False, False),
    (P, T, CHANGE_STATUS_ANY, True, False, False),
    (P, R, CHANGE_STATUS_ANY, True, True, False),
    (R, D, REVIEW, False, False, True),
    (R, P, REVIEW, False, False, True),
    (D, P, CHANGE_STATUS_ANY, False, False, False),
]

VALIDAS = {(fila[0], fila[1]) for fila in TABLA}

# "Cualquier transición que no aparezca en esta tabla se rechaza": the other 17
# ordered pairs, self-transitions included.
INVALIDAS = [
    par for par in itertools.product(TaskStatus, repeat=2) if par not in VALIDAS
]


@pytest.mark.parametrize(
    ("source", "target", "permission", "assignee_may", "requires_submission", "via_review"),
    TABLA,
)
def test_transicion_valida_con_sus_exigencias(
    source, target, permission, assignee_may, requires_submission, via_review
):
    transition = state_machine.find(source, target)

    assert transition is not None, f"falta la transición {source} → {target}"
    assert transition.permission == permission
    assert transition.assignee_may is assignee_may
    assert transition.requires_submission is requires_submission
    assert transition.via_review_only is via_review


@pytest.mark.parametrize(("source", "target"), INVALIDAS)
def test_transicion_no_permitida(source, target):
    # En particular: no se salta de TODO a DONE, ni de IN_REVIEW a TODO, ni de
    # BACKLOG a IN_PROGRESS.
    assert state_machine.find(source, target) is None


def test_la_tabla_no_tiene_filas_de_mas():
    assert len(state_machine.TRANSITIONS) == len(TABLA)


@pytest.mark.parametrize(
    ("source", "esperados"),
    [
        (B, [T]),
        (T, [P, B]),
        (P, [T, R]),
        (R, [D, P]),
        (D, [P]),
    ],
)
def test_enumera_los_destinos_validos(source, esperados):
    # El 409 tiene que decir a dónde sí se puede ir, no solo que no.
    assert state_machine.allowed_targets(source) == esperados


# --- Quién puede mover qué (RN-10) ---


@pytest.mark.parametrize(("source", "target"), [(T, P), (P, T), (P, R)])
def test_el_responsable_mueve_su_tarea_sin_permisos_especiales(source, target):
    # Un rol con solo task.view y task.comment basta si la tarea es suya.
    transition = state_machine.find(source, target)
    assert transition is not None
    assert transition.allows(permissions=frozenset({"task.view"}), is_assignee=True)


@pytest.mark.parametrize(("source", "target"), [(T, P), (P, T), (P, R)])
def test_quien_no_es_responsable_necesita_el_permiso(source, target):
    transition = state_machine.find(source, target)
    assert transition is not None
    assert not transition.allows(permissions=frozenset({"task.view"}), is_assignee=False)
    assert transition.allows(
        permissions=frozenset({"task.view", CHANGE_STATUS_ANY}), is_assignee=False
    )


@pytest.mark.parametrize(("source", "target"), [(B, T), (T, B), (D, P)])
def test_ser_responsable_no_alcanza_donde_la_tabla_no_lo_concede(source, target):
    # BACKLOG ↔ TODO y la reapertura son del líder, no del responsable.
    transition = state_machine.find(source, target)
    assert transition is not None
    assert not transition.allows(permissions=frozenset({"task.view"}), is_assignee=True)
    assert transition.allows(
        permissions=frozenset({CHANGE_STATUS_ANY}), is_assignee=False
    )


@pytest.mark.parametrize(("source", "target"), [(R, D), (R, P)])
def test_solo_task_review_saca_una_tarea_de_revision(source, target):
    # RN-07: ni el responsable, ni quien solo puede mover tareas ajenas.
    transition = state_machine.find(source, target)
    assert transition is not None
    assert not transition.allows(permissions=frozenset({CHANGE_STATUS_ANY}), is_assignee=True)
    assert transition.allows(permissions=frozenset({REVIEW}), is_assignee=False)
