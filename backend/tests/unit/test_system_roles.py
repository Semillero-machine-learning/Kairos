"""The permission catalog and the default project roles (business-rules.md 2, 3).

These two lists exist twice: once in migration 0001, which seeds the catalog
table, and once in app/modules/projects/constants.py, which the service reads.
The point of this file is that they can never drift apart in silence.
"""

import importlib.util
import pathlib

from app.modules.projects.constants import (
    PERMISSION_CODES,
    SYSTEM_ROLES,
    VIEW_PERMISSION,
)


def _load_catalog_migration():
    """alembic/versions is not an importable package, so the seed migration is
    loaded from its path to compare it against the constants."""
    path = (
        pathlib.Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "0001_permissions_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("_catalog_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# The catalog is closed on purpose: 14 codes, not one more without an explicit
# decision (business-rules.md 3, roadmap risk table).
EXPECTED_CATALOG_SIZE = 14


def test_el_catalogo_tiene_catorce_permisos():
    assert len(PERMISSION_CODES) == EXPECTED_CATALOG_SIZE
    assert len(set(PERMISSION_CODES)) == EXPECTED_CATALOG_SIZE


def test_el_catalogo_coincide_con_la_migracion():
    seeded = {code for code, _category, _description in _load_catalog_migration().PERMISSIONS}
    assert seeded == set(PERMISSION_CODES)


def test_hay_tres_roles_del_sistema():
    assert [role.name for role in SYSTEM_ROLES] == ["Líder", "Colaborador", "Observador"]


def test_el_lider_tiene_todos_los_permisos():
    leader = SYSTEM_ROLES[0]
    assert leader.permissions == set(PERMISSION_CODES)
    assert leader.color == "#1F6F5C"


def test_colaborador_y_observador_solo_ven_y_comentan():
    collaborator, observer = SYSTEM_ROLES[1], SYSTEM_ROLES[2]
    expected = {"task.view", "task.comment"}
    assert collaborator.permissions == expected
    assert observer.permissions == expected
    # They differ by intent, not by catalog: what separates them is the implicit
    # ownership rules of business-rules.md 5.
    assert collaborator.color != observer.color


def test_todo_rol_del_sistema_puede_ver_el_proyecto():
    # RN-05 applies to the defaults too, not only to custom roles.
    for role in SYSTEM_ROLES:
        assert VIEW_PERMISSION in role.permissions
