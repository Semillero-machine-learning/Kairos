"""The permission catalog endpoint (api-contract.md 4).

Any authenticated user may read it: it is the list the role editor draws its
checkboxes from, and it reveals nothing about any particular project.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.projects.schemas import PermissionRead
from app.modules.projects.service import ProjectsService
from app.modules.users.models import User

router = APIRouter(prefix="/permissions", tags=["projects"])


@router.get("", response_model=list[PermissionRead])
async def list_permissions(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PermissionRead]:
    permissions = await ProjectsService(db).list_permissions()
    return [PermissionRead.model_validate(p) for p in permissions]
