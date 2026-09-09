"""Pydantic schemas for the lessons module (api-contract.md 8)."""

import datetime
import re
import uuid

from pydantic import BaseModel, Field, field_validator

from app.core.enums import ResourceType

# RN-34: the platform hosts nothing, so every resource is an external address.
# The database repeats this check as a CHECK constraint on the column.
EXTERNAL_URL_PATTERN = re.compile(r"^https?://\S+$")

EXTERNAL_URL_HELP = (
    "El enlace debe empezar por http:// o https:// y apuntar a una dirección externa."
)


def _strip(value: object) -> object:
    """Trim before the length constraint runs, so the check sees what will be
    stored. Same reasoning as tasks/schemas.py."""
    return value.strip() if isinstance(value, str) else value


# --- Resources ---


class LessonResourceRead(BaseModel):
    id: uuid.UUID
    type: ResourceType
    title: str
    url: str
    position: int


# --- Lessons ---


class LessonRead(BaseModel):
    """A lesson as it travels inside the catalog tree.

    Carries the number of resources, not the resources themselves: the tree is
    for browsing and the list of links belongs to the lesson's own screen. The
    count is computed on read, never stored (data-model.md 8).
    """

    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    description: str | None
    position: int
    is_published: bool
    resource_count: int


class LessonDetail(BaseModel):
    """GET /lessons/{id}: the lesson with its links, ready to study from.

    ``module_title`` travels with it so a direct link to a lesson can say which
    module it belongs to without a second request.
    """

    id: uuid.UUID
    module_id: uuid.UUID
    module_title: str
    title: str
    description: str | None
    position: int
    is_published: bool
    resources: list[LessonResourceRead]
    created_at: datetime.datetime
    updated_at: datetime.datetime


class LessonCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    _trim_title = field_validator("title", mode="before")(_strip)


class LessonUpdate(BaseModel):
    """Content only, like the module's PATCH and for the same reason."""

    title: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    _trim_title = field_validator("title", mode="before")(_strip)

    @field_validator("title")
    @classmethod
    def _title_is_never_null(cls, title: str | None) -> str | None:
        if title is None:
            raise ValueError("El título de la lección no puede quedar vacío.")
        return title


class LessonResourceCreate(BaseModel):
    """A link and what kind of material is on the other end (RF-48)."""

    type: ResourceType
    title: str = Field(min_length=1, max_length=200)
    url: str = Field(min_length=1, max_length=2000)

    _trim_title = field_validator("title", mode="before")(_strip)
    _trim_url = field_validator("url", mode="before")(_strip)

    @field_validator("url")
    @classmethod
    def _is_external(cls, url: str) -> str:
        """RN-34: the platform hosts nothing, so a resource is always an address
        somewhere else. The column repeats the check as a CHECK constraint."""
        if not EXTERNAL_URL_PATTERN.match(url):
            raise ValueError(EXTERNAL_URL_HELP)
        return url


# --- Modules ---


class LessonModuleRead(BaseModel):
    """A module and its visible lessons.

    What "visible" means depends on who is asking, and the service decides it:
    an editor sees the drafts, everybody else does not (RN-32, RN-33).
    """

    id: uuid.UUID
    title: str
    description: str | None
    position: int
    is_published: bool
    lessons: list[LessonRead]
    created_at: datetime.datetime
    updated_at: datetime.datetime


class LessonModuleCreate(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    _trim_title = field_validator("title", mode="before")(_strip)


class LessonModuleUpdate(BaseModel):
    """Content only. Publishing goes through its own endpoint and ordering
    through the reorder one, so there is a single way to make each change.

    ``description`` is genuinely nullable, so sending null clears it; ``title``
    is a NOT NULL column and an explicit null has to be refused here rather than
    reaching the database.
    """

    title: str | None = Field(default=None, min_length=3, max_length=150)
    description: str | None = Field(default=None, max_length=2000)

    _trim_title = field_validator("title", mode="before")(_strip)

    @field_validator("title")
    @classmethod
    def _title_is_never_null(cls, title: str | None) -> str | None:
        if title is None:
            raise ValueError("El título del módulo no puede quedar vacío.")
        return title


# --- Shared bodies ---


class PublishBody(BaseModel):
    """One endpoint for both directions (RF-47).

    Publishing and unpublishing are the same decision with opposite values, and
    two endpoints for it would be two places to forget a rule.
    """

    published: bool = True


class ReorderBody(BaseModel):
    """The complete new order, not a move of one element (RF-50).

    Sending every identifier lets the server check that the list matches exactly
    what exists, which catches a stale interface — somebody reordering a catalog
    another editor changed underneath — instead of silently writing a hole in
    the sequence.
    """

    ids: list[uuid.UUID] = Field(min_length=1)

    @field_validator("ids")
    @classmethod
    def _no_duplicates(cls, ids: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(ids)) != len(ids):
            raise ValueError("La lista de orden tiene identificadores repetidos.")
        return ids
