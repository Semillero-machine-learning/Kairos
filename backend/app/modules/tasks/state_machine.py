"""The task lifecycle, transcribed from business-rules.md 4.

The transition table is **data, not control flow**. Every rule about who may move
a task and what the move demands lives in ``TRANSITIONS``; the service reads the
table and never grows an ``if`` of its own about permissions. That is what makes
the mandatory unit coverage meaningful: the test walks all 25 ordered pairs of
states and compares them against this tuple, so a rule that is wrong here fails
there, instead of hiding inside a service method nobody re-reads.

Two rules shape the table beyond "which arrows exist":

* **RN-10 (ownership).** An assignee moves their own task between TODO and
  IN_PROGRESS, and on to IN_REVIEW, without holding ``task.change_status_any``.
  Anyone else needs the permission. ``assignee_may`` is that distinction.
* **RN-07 / RN-09 (review).** The two arrows leaving IN_REVIEW are marked
  ``via_review_only``. Approving has to stamp the submission and reopening has to
  carry a comment, and a bare status change can do neither — those two go through
  the submission review endpoint, never through POST /tasks/{id}/status.
"""

from dataclasses import dataclass

from app.core.enums import TaskStatus

CHANGE_STATUS_ANY = "task.change_status_any"
REVIEW = "task.review"


@dataclass(frozen=True)
class Transition:
    source: TaskStatus
    target: TaskStatus
    #: Permission that authorizes this move for anyone.
    permission: str
    #: Whether an assignee may make the move without that permission (RN-10).
    assignee_may: bool
    #: Whether the move demands a pending submission (RF-31).
    requires_submission: bool
    #: Whether the move belongs to the review endpoint (RN-07, RN-09).
    via_review_only: bool

    def allows(self, *, permissions: frozenset[str], is_assignee: bool) -> bool:
        """Whether this user may make this move. No permission implies another
        (RN-06): the table says exactly which one counts."""
        if self.permission in permissions:
            return True
        return self.assignee_may and is_assignee


# business-rules.md 4, row for row. Anything absent from this tuple is refused.
TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        source=TaskStatus.BACKLOG,
        target=TaskStatus.TODO,
        permission=CHANGE_STATUS_ANY,
        assignee_may=False,
        requires_submission=False,
        via_review_only=False,
    ),
    Transition(
        source=TaskStatus.TODO,
        target=TaskStatus.IN_PROGRESS,
        permission=CHANGE_STATUS_ANY,
        assignee_may=True,
        requires_submission=False,
        via_review_only=False,
    ),
    Transition(
        source=TaskStatus.TODO,
        target=TaskStatus.BACKLOG,
        permission=CHANGE_STATUS_ANY,
        assignee_may=False,
        requires_submission=False,
        via_review_only=False,
    ),
    Transition(
        source=TaskStatus.IN_PROGRESS,
        target=TaskStatus.TODO,
        permission=CHANGE_STATUS_ANY,
        assignee_may=True,
        requires_submission=False,
        via_review_only=False,
    ),
    Transition(
        source=TaskStatus.IN_PROGRESS,
        target=TaskStatus.IN_REVIEW,
        permission=CHANGE_STATUS_ANY,
        assignee_may=True,
        requires_submission=True,
        via_review_only=False,
    ),
    Transition(
        source=TaskStatus.IN_REVIEW,
        target=TaskStatus.DONE,
        permission=REVIEW,
        assignee_may=False,
        requires_submission=False,
        via_review_only=True,
    ),
    Transition(
        source=TaskStatus.IN_REVIEW,
        target=TaskStatus.IN_PROGRESS,
        permission=REVIEW,
        assignee_may=False,
        requires_submission=False,
        via_review_only=True,
    ),
    Transition(
        # Reopening. completed_at goes back to null (RN-08).
        source=TaskStatus.DONE,
        target=TaskStatus.IN_PROGRESS,
        permission=CHANGE_STATUS_ANY,
        assignee_may=False,
        requires_submission=False,
        via_review_only=False,
    ),
)

_BY_PAIR: dict[tuple[TaskStatus, TaskStatus], Transition] = {
    (t.source, t.target): t for t in TRANSITIONS
}


def find(source: TaskStatus, target: TaskStatus) -> Transition | None:
    """The transition between two states, or None if the table has no such row."""
    return _BY_PAIR.get((source, target))


def allowed_targets(source: TaskStatus) -> list[TaskStatus]:
    """Every state reachable from ``source``, in table order.

    Used to build the 409 message, which has to enumerate the valid moves rather
    than just say no (HU-08, "Transición no permitida").
    """
    return [t.target for t in TRANSITIONS if t.source == source]
