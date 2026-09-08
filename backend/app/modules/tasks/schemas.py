"""Pydantic schemas for the tasks module (api-contract.md 5 and 6)."""

import datetime
import re
import uuid

from pydantic import BaseModel, Field, field_validator

from app.core.enums import SubmissionReviewStatus, TaskPeriodicity, TaskStatus

# RF-32: a submission points at work already on GitHub — a commit, a pull
# request or a repository tree. The platform stores no files (RN-34), and the
# database repeats the loose half of this check as a CHECK constraint.
GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+"
    r"(/(commit/[0-9a-fA-F]{7,40}|pull/\d+|tree/\S+))?/?$"
)

GITHUB_URL_HELP = (
    "El enlace debe apuntar a GitHub: un commit "
    "(https://github.com/usuario/repositorio/commit/abc1234), un pull request "
    "(.../pull/12) o el árbol del repositorio (.../tree/main)."
)


def _strip(value: object) -> object:
    """Trim before the length constraint runs, so the check sees what will be
    stored. Same reasoning as projects/schemas.py."""
    return value.strip() if isinstance(value, str) else value


class UserRef(BaseModel):
    """Minimal user shape, declared here so the tasks module never leaks another
    module's full schema into its responses."""

    id: uuid.UUID
    full_name: str
    email: str


class ProjectRef(BaseModel):
    """Just enough project to label a row in «Mis tareas» (RF-36)."""

    id: uuid.UUID
    name: str


# --- Tasks ---


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    periodicity: TaskPeriodicity = TaskPeriodicity.ONE_TIME
    # Accepted even if it is in the past: a task can be registered late, and the
    # warning is the interface's job (EB-10).
    due_date: datetime.date | None = None
    assignee_ids: list[uuid.UUID] = Field(default_factory=list)

    _trim_title = field_validator("title", mode="before")(_strip)

    @field_validator("assignee_ids")
    @classmethod
    def _no_duplicates(cls, ids: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(ids)) != len(ids):
            raise ValueError("La lista de responsables tiene identificadores repetidos.")
        return ids


class TaskUpdate(BaseModel):
    """Every field optional: a PATCH only touches what it carries.

    ``description`` and ``due_date`` are genuinely nullable, so sending null
    clears them; ``title`` and ``periodicity`` are NOT NULL columns and an
    explicit null has to be refused here rather than reaching the database.
    """

    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    periodicity: TaskPeriodicity | None = None
    due_date: datetime.date | None = None

    _trim_title = field_validator("title", mode="before")(_strip)

    @field_validator("title")
    @classmethod
    def _title_is_never_null(cls, title: str | None) -> str | None:
        if title is None:
            raise ValueError("El título de la tarea no puede quedar vacío.")
        return title

    @field_validator("periodicity")
    @classmethod
    def _periodicity_is_never_null(
        cls, periodicity: TaskPeriodicity | None
    ) -> TaskPeriodicity | None:
        if periodicity is None:
            raise ValueError("La periodicidad no puede quedar vacía.")
        return periodicity


class TaskRead(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str | None
    status: TaskStatus
    periodicity: TaskPeriodicity
    due_date: datetime.date | None
    # Derived on read, never stored (data-model.md 8). It travels in the response
    # so the badge on the card and the ?overdue=true filter cannot disagree:
    # both are the server comparing against today's date in Bogotá.
    is_overdue: bool
    assignees: list[UserRef]
    created_by: UserRef
    completed_at: datetime.datetime | None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class MyTaskRead(TaskRead):
    """A row of GET /me/tasks: the task plus the project it belongs to."""

    project: ProjectRef


class TasksPage(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    size: int


class MyTasksPage(BaseModel):
    items: list[MyTaskRead]
    total: int
    page: int
    size: int


class TaskStatusChange(BaseModel):
    status: TaskStatus


class AssigneeAdd(BaseModel):
    user_id: uuid.UUID


# --- Submissions ---


class SubmissionCreate(BaseModel):
    description: str = Field(min_length=10, max_length=4000)
    commit_url: str | None = None

    _trim_description = field_validator("description", mode="before")(_strip)

    @field_validator("commit_url", mode="before")
    @classmethod
    def _blank_is_absent(cls, url: object) -> object:
        """An empty text field arrives as "" from a form; store it as absent."""
        if isinstance(url, str) and not url.strip():
            return None
        return url.strip() if isinstance(url, str) else url

    @field_validator("commit_url")
    @classmethod
    def _looks_like_github(cls, url: str | None) -> str | None:
        if url is not None and not GITHUB_URL_PATTERN.match(url):
            raise ValueError(GITHUB_URL_HELP)
        return url


class SubmissionRead(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    submitted_by: UserRef
    description: str
    commit_url: str | None
    review_status: SubmissionReviewStatus
    reviewed_by: UserRef | None
    reviewed_at: datetime.datetime | None
    review_comment: str | None
    created_at: datetime.datetime


class SubmissionUpdate(BaseModel):
    """Correcting your own submission while nobody has looked at it yet (RN-12).

    Both fields are optional, like every PATCH in this API. ``commit_url`` is
    genuinely nullable, so sending null clears the link; ``description`` is a
    NOT NULL column and an explicit null has to be refused here.
    """

    description: str | None = Field(default=None, min_length=10, max_length=4000)
    commit_url: str | None = None

    _trim_description = field_validator("description", mode="before")(_strip)

    @field_validator("commit_url", mode="before")
    @classmethod
    def _blank_is_absent(cls, url: object) -> object:
        if isinstance(url, str) and not url.strip():
            return None
        return url.strip() if isinstance(url, str) else url

    @field_validator("commit_url")
    @classmethod
    def _looks_like_github(cls, url: str | None) -> str | None:
        if url is not None and not GITHUB_URL_PATTERN.match(url):
            raise ValueError(GITHUB_URL_HELP)
        return url

    @field_validator("description")
    @classmethod
    def _description_is_never_null(cls, description: str | None) -> str | None:
        if description is None:
            raise ValueError("La descripción de la entrega no puede quedar vacía.")
        return description


class SubmissionReview(BaseModel):
    """Approve or send back (RF-33).

    The comment is optional *here* on purpose: returning without one is a
    business rule (RN-09), and the service refuses it with the specific code
    REVIEW_COMMENT_REQUIRED that api-contract.md 6 promises. A validator would
    answer VALIDATION_ERROR instead and the frontend could not tell the two
    apart.
    """

    approved: bool
    comment: str | None = Field(default=None, max_length=4000)

    @field_validator("comment", mode="before")
    @classmethod
    def _blank_is_absent(cls, comment: object) -> object:
        if isinstance(comment, str) and not comment.strip():
            return None
        return comment.strip() if isinstance(comment, str) else comment


# --- Comments ---


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    _trim_body = field_validator("body", mode="before")(_strip)


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)

    _trim_body = field_validator("body", mode="before")(_strip)


class CommentRead(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    author: UserRef
    body: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
