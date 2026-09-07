"""The closed permission catalog and the three default project roles.

Both lists are transcriptions of business-rules.md sections 2 and 3. They are
kept here, next to the code that reads them, and asserted against the catalog
migration by tests/unit/test_system_roles.py, so the two copies cannot drift.
"""

from dataclasses import dataclass

# The catalog is closed: 14 codes, not one more without an explicit decision.
PERMISSION_CODES: tuple[str, ...] = (
    "task.view",
    "task.comment",
    "task.create",
    "task.edit_any",
    "task.delete",
    "task.assign",
    "task.change_status_any",
    "task.review",
    "member.add",
    "member.remove",
    "role.assign",
    "role.manage",
    "project.edit",
    "project.archive",
)

# Required in every role: a role that cannot see the project is meaningless (RN-05).
VIEW_PERMISSION = "task.view"

# Permissions that only read. An archived project still answers these (RF-18);
# everything else is rejected while it stays archived (RN-15).
READ_ONLY_PERMISSIONS: frozenset[str] = frozenset({VIEW_PERMISSION})

# Keeps a project administrable: RN-14 refuses any change that would leave the
# project without a member holding it.
PROJECT_ADMIN_PERMISSION = "project.archive"


@dataclass(frozen=True)
class SystemRoleSpec:
    name: str
    color: str
    permissions: frozenset[str]


# Created inside the same transaction as the project (RF-14). Collaborator and
# Observer share their permission set on purpose: what separates them is the
# implicit ownership rules of business-rules.md 5, not the catalog.
SYSTEM_ROLES: tuple[SystemRoleSpec, ...] = (
    SystemRoleSpec(name="Líder", color="#1F6F5C", permissions=frozenset(PERMISSION_CODES)),
    SystemRoleSpec(
        name="Colaborador",
        color="#2E5C8A",
        permissions=frozenset({"task.view", "task.comment"}),
    ),
    SystemRoleSpec(
        name="Observador",
        color="#6B6B6B",
        permissions=frozenset({"task.view", "task.comment"}),
    ),
)

LEADER_ROLE_NAME = SYSTEM_ROLES[0].name
