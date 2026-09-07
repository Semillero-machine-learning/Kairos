"""Pydantic schemas for the projects module (api-contract.md 3 and 4)."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import ProjectStatus

COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


class PermissionRead(BaseModel):
    """One entry of the closed catalog, used to build the role editor."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    description: str
    category: str


# --- Projects ---


def _strip(value: object) -> object:
    """Trim before the length constraint runs, not after.

    An "after" validator would let ``"  A  "`` through a ``min_length=2`` check
    and then hand the database a one-character name, which the CHECK constraint
    rejects as a 500. Trimming first makes the constraint see what will actually
    be stored.
    """
    return value.strip() if isinstance(value, str) else value


class ProjectCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    start_date: datetime.date | None = None
    leader_user_id: uuid.UUID

    _trim_name = field_validator("name", mode="before")(_strip)


class ProjectUpdate(BaseModel):
    """Every field optional: a PATCH only touches what it carries.

    ``description`` and ``start_date`` are genuinely nullable, so sending null
    clears them. ``name`` is not: the column is NOT NULL, and an explicit null
    has to be refused here rather than reaching the database.
    """

    name: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=4000)
    start_date: datetime.date | None = None

    _trim_name = field_validator("name", mode="before")(_strip)

    @field_validator("name")
    @classmethod
    def _name_is_never_null(cls, name: str | None) -> str | None:
        if name is None:
            raise ValueError("El nombre del proyecto no puede quedar vacío.")
        return name


class UserRef(BaseModel):
    """Minimal user shape, so the projects module never leaks another module's
    full schema into its responses."""

    id: uuid.UUID
    full_name: str
    email: str


class MyRole(BaseModel):
    id: uuid.UUID
    name: str
    color: str


class ProjectListItem(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    start_date: datetime.date | None
    member_count: int
    # Null for a global ADMIN looking at a project they do not belong to.
    my_role: MyRole | None
    created_at: datetime.datetime


class ProjectsPage(BaseModel):
    items: list[ProjectListItem]
    total: int
    page: int
    size: int


class TaskCounts(BaseModel):
    """Board tallies, counted on every read. Soft-deleted tasks are not in them
    (RF-37), so the five values add up to what the board actually shows."""

    BACKLOG: int = 0
    TODO: int = 0
    IN_PROGRESS: int = 0
    IN_REVIEW: int = 0
    DONE: int = 0


class ProjectDetail(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    status: ProjectStatus
    start_date: datetime.date | None
    archived_at: datetime.datetime | None
    member_count: int
    task_counts: TaskCounts
    my_permissions: list[str]
    my_role: MyRole | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


# --- Members ---


class MemberAdd(BaseModel):
    user_id: uuid.UUID
    project_role_id: uuid.UUID


class MemberRoleChange(BaseModel):
    project_role_id: uuid.UUID


class MemberRead(BaseModel):
    user: UserRef
    role: MyRole
    joined_at: datetime.datetime


# --- Roles ---


class RoleWrite(BaseModel):
    name: str = Field(min_length=2, max_length=40)
    color: str = Field(pattern=COLOR_PATTERN)
    permissions: list[str] = Field(min_length=1)

    @field_validator("permissions")
    @classmethod
    def _no_duplicates(cls, codes: list[str]) -> list[str]:
        if len(set(codes)) != len(codes):
            raise ValueError("La lista de permisos tiene códigos repetidos.")
        return codes

    _trim_name = field_validator("name", mode="before")(_strip)


class RoleRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    color: str
    is_system: bool
    permissions: list[str]
    # RN-19: who created a custom role, shown in the role editor. Null on the
    # three system roles, which nobody creates by hand.
    created_by: UserRef | None
    member_count: int
    created_at: datetime.datetime
