"""Domain enums shared across modules.

These live in core because more than one module and the auth/JWT layer reference
them; keeping them here avoids a module importing another module's models just
to reuse a type. The PostgreSQL ENUM types themselves are created by migrations;
each model binds to them with create_type=False.
"""

import enum


class GlobalRole(enum.StrEnum):
    ADMIN = "ADMIN"
    LESSON_EDITOR = "LESSON_EDITOR"
    MEMBER = "MEMBER"


class UserStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class ProjectStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class TaskStatus(enum.StrEnum):
    """The five fixed states of a task (RF-28).

    Declaration order is board order, left to right, and the transition table in
    tasks/state_machine.py is what says which jumps between them are legal.
    """

    BACKLOG = "BACKLOG"
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"


class TaskPeriodicity(enum.StrEnum):
    """A descriptive label, nothing more (RF-26).

    It never generates a task: it exists so the board can be filtered and so the
    team reads the intended rhythm off the card.
    """

    ONE_TIME = "ONE_TIME"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    SEMESTER = "SEMESTER"


class SubmissionReviewStatus(enum.StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ResourceType(enum.StrEnum):
    """What a lesson resource points at (RF-48).

    The list is closed and describes the *material*, not where it is hosted: the
    platform stores no files (RN-34), so every one of these is an external URL
    and the type only tells the interface which icon and which wording to use.
    """

    NOTEBOOK = "NOTEBOOK"
    PDF = "PDF"
    VIDEO = "VIDEO"
    REPOSITORY = "REPOSITORY"
    ARTICLE = "ARTICLE"


class NotificationKind(enum.StrEnum):
    """What a notification is about (data-model.md 2).

    The invitation and the password reset are not here: those emails go out
    before the person has an account to read an in-app notification with, so
    they have no row in ``notifications`` (RN-25 lists them as events, not as
    inbox entries).
    """

    TASK_ASSIGNED = "TASK_ASSIGNED"
    TASK_DUE_SOON = "TASK_DUE_SOON"
    TASK_OVERDUE = "TASK_OVERDUE"
    SUBMISSION_APPROVED = "SUBMISSION_APPROVED"
    SUBMISSION_REJECTED = "SUBMISSION_REJECTED"


class DispatchStatus(enum.StrEnum):
    """How the email of a scheduled reminder ended up.

    Two values, no PENDING: the row is written before the send as the idempotency
    claim (RN-27), so it starts as SENT and is corrected to FAILED if the
    provider refuses. A third state would suggest the job resumes half-finished
    work, and it does not — RN-29 says it never rebuilds the past.
    """

    SENT = "SENT"
    FAILED = "FAILED"
