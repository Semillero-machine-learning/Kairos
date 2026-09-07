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
