"""The bell: one user's own notifications (api-contract.md 7).

No project guard anywhere here. A notification belongs to a person, not to a
project, and the service scopes every read and write by the caller's id — which
is also why somebody else's notification answers 404 rather than 403.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.pagination import Pagination
from app.modules.notifications.schemas import (
    MarkAllReadResult,
    NotificationRead,
    NotificationsPage,
    UnreadCount,
)
from app.modules.notifications.service import NotificationsService
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationsPage)
async def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationsPage:
    items, total = await NotificationsService(db).list_inbox(
        current_user.id,
        unread_only=unread_only,
        pagination=Pagination(page=page, size=size),
    )
    return NotificationsPage(
        items=[NotificationRead.model_validate(item, from_attributes=True) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/unread-count", response_model=UnreadCount)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCount:
    """Polled every 60 seconds by every visible tab, so it stays a count and
    nothing else (api-contract.md 7)."""
    return UnreadCount(unread=await NotificationsService(db).unread_count(current_user.id))


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationRead:
    notification = await NotificationsService(db).mark_read(
        notification_id, current_user.id
    )
    return NotificationRead.model_validate(notification, from_attributes=True)


@router.post("/read-all", response_model=MarkAllReadResult, status_code=status.HTTP_200_OK)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MarkAllReadResult:
    return MarkAllReadResult(marked=await NotificationsService(db).mark_all_read(current_user.id))
