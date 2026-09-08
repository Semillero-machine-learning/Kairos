"""System endpoints mounted at the root, outside /api/v1.

/health runs a SELECT 1 so it doubles as a liveness probe and as the request
that keeps Render and Supabase awake (RNF-02, RNF-07).

/internal/jobs/reminders is the trigger for the scheduled job. Render's free
plan has no cron, so the schedule lives in GitHub Actions and reaches the
application through this endpoint (architecture.md 4).
"""

import secrets

from fastapi import APIRouter, Depends, Header
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError
from app.jobs.reminders import run_reminders
from app.modules.notifications.schemas import ReminderJobSummary

router = APIRouter(tags=["system"])


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


async def require_job_token(
    x_job_token: str | None = Header(default=None, alias="X-Job-Token"),
) -> None:
    """Authenticate the scheduler, which has no user and therefore no JWT.

    Two details that matter more than they look:

    * ``compare_digest`` rather than ``==``, so the comparison takes the same
      time whatever the wrong token was.
    * An unset ``JOB_TOKEN`` closes the endpoint instead of opening it. A missing
      secret must never be the same thing as a matching one — that is how an
      internal endpoint ends up public on a fresh deployment.
    """
    expected = get_settings().job_token
    if not expected or not x_job_token:
        raise AuthenticationError("Se requiere un token de trabajo válido.")
    if not secrets.compare_digest(x_job_token, expected):
        raise AuthenticationError("Se requiere un token de trabajo válido.")


@router.post(
    "/internal/jobs/reminders",
    response_model=ReminderJobSummary,
    # Out of the public schema (api-contract.md 9): documenting the trigger of
    # the whole notification system next to the login endpoint invites traffic
    # it has no reason to receive.
    include_in_schema=False,
    dependencies=[Depends(require_job_token)],
)
async def trigger_reminders(db: AsyncSession = Depends(get_db)) -> ReminderJobSummary:
    """Run today's reminders and answer with the summary of the run.

    Safe to call twice: the second run reports its sends as skipped duplicates
    and delivers nothing (RN-27). That is the property the GitHub Actions cron
    depends on, because it retries and occasionally fires late (RN-29).
    """
    return await run_reminders(db)
