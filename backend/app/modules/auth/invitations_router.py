"""Admin endpoints for platform invitations (/invitations). HTTP only."""

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_global_role
from app.core.enums import GlobalRole
from app.modules.auth.models import InvitationStatus
from app.modules.auth.schemas import (
    InvitationCreate,
    InvitationCreatedResponse,
    InvitationRead,
)
from app.modules.auth.service import AuthService
from app.modules.users.models import User

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get("", response_model=list[InvitationRead])
async def list_invitations(
    status: InvitationStatus | None = None,
    _: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[InvitationRead]:
    invitations = await AuthService(db).list_invitations(status)
    return [InvitationRead.model_validate(inv) for inv in invitations]


@router.post("", response_model=InvitationCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    body: InvitationCreate,
    admin: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> InvitationCreatedResponse:
    invitation, invite_url = await AuthService(db).create_invitation(
        admin, body.email, body.global_role
    )
    return InvitationCreatedResponse(
        id=invitation.id,
        email=invitation.email,
        global_role=invitation.global_role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        invite_url=invite_url,
    )


@router.post("/{invitation_id}/resend", response_model=InvitationCreatedResponse)
async def resend_invitation(
    invitation_id: uuid.UUID,
    _: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> InvitationCreatedResponse:
    invitation, invite_url = await AuthService(db).resend_invitation(invitation_id)
    return InvitationCreatedResponse(
        id=invitation.id,
        email=invitation.email,
        global_role=invitation.global_role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        invite_url=invite_url,
    )


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    _: User = Depends(require_global_role(GlobalRole.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await AuthService(db).revoke_invitation(invitation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
