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
