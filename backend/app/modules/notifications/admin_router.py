"""The global reminder configuration (api-contract.md 7, RF-43).

One row for the whole platform and only an ADMIN touches it. There is no
per-project variant and there should not be one: RF-43 is explicit that the
configuration is global, and RN-26 pins the timezone so it cannot be changed at
all.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_global_role
from app.core.enums import GlobalRole
from app.modules.notifications.schemas import (
    NotificationSettingsRead,
    NotificationSettingsUpdate,
)
from app.modules.notifications.service import NotificationsService
from app.modules.users.models import User

router = APIRouter(prefix="/admin/notification-settings", tags=["notifications"])


@router.get("", response_model=NotificationSettingsRead)
async def get_notification_settings(
    _admin: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsRead:
    settings = await NotificationsService(db).get_settings()
    return NotificationSettingsRead.model_validate(settings, from_attributes=True)


@router.put("", response_model=NotificationSettingsRead)
async def update_notification_settings(
    body: NotificationSettingsUpdate,
    admin: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsRead:
    """A project leader whose global role is MEMBER gets a 403 here: leading a
    project says nothing about the platform-wide configuration (HU-11)."""
    settings = await NotificationsService(db).update_settings(
        reminder_days_before=body.reminder_days_before,
        send_hour=body.send_hour,
        overdue_enabled=body.overdue_enabled,
        updated_by=admin.id,
    )
    return NotificationSettingsRead.model_validate(settings, from_attributes=True)
