"""Service views to response schemas.

Three routers answer with the same shapes, so the mapping lives once here
instead of being copied into each of them. Pure translation: no queries, no
decisions.
"""

from app.modules.tasks.schemas import (
    MyTaskRead,
    ProjectRef,
    SubmissionRead,
    TaskRead,
    UserRef,
)
from app.modules.tasks.service import (
    MyTaskView,
    SubmissionView,
    TaskView,
    UserSummary,
)


def user_ref(person: UserSummary) -> UserRef:
    return UserRef(id=person.id, full_name=person.full_name, email=person.email)


def task_read(view: TaskView) -> TaskRead:
    task = view.task
    return TaskRead(
        id=task.id,
        project_id=task.project_id,
        title=task.title,
        description=task.description,
        status=task.status,
        periodicity=task.periodicity,
        due_date=task.due_date,
        is_overdue=view.is_overdue,
        assignees=[user_ref(person) for person in view.assignees],
        created_by=user_ref(view.creator),
        completed_at=task.completed_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def my_task_read(row: MyTaskView) -> MyTaskRead:
    return MyTaskRead(
        **task_read(row.view).model_dump(),
        project=ProjectRef(id=row.project_id, name=row.project_name),
    )


def submission_read(view: SubmissionView) -> SubmissionRead:
    submission = view.submission
    return SubmissionRead(
        id=submission.id,
        task_id=submission.task_id,
        submitted_by=user_ref(view.submitted_by),
        description=submission.description,
        commit_url=submission.commit_url,
        review_status=submission.review_status,
        reviewed_by=user_ref(view.reviewed_by) if view.reviewed_by else None,
        reviewed_at=submission.reviewed_at,
        review_comment=submission.review_comment,
        created_at=submission.created_at,
    )
