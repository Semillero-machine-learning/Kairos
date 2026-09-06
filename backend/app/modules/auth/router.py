"""HTTP endpoints for auth. No business logic or queries live here."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import (
    AcceptInvitationRequest,
    ChangePasswordRequest,
    InvitationTokenInfo,
    LoginRequest,
    LogoutRequest,
    MeRead,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RefreshRequest,
    TokenResponse,
    UpdateMeRequest,
    UserRead,
)
from app.modules.auth.service import AuthService, IssuedTokens
from app.modules.users.models import User
from app.modules.users.service import UsersService

router = APIRouter(prefix="/auth", tags=["auth"])

_RESET_REQUEST_MESSAGE = (
    "Si el correo está registrado, enviamos un enlace para restablecer la contraseña."
)


def _token_response(issued: IssuedTokens, expires_in: int) -> TokenResponse:
    return TokenResponse(
        access_token=issued.access_token,
        refresh_token=issued.refresh_token,
        expires_in=expires_in,
        user=UserRead.model_validate(issued.user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    issued = await service.login(
        body.email, body.password, user_agent=request.headers.get("user-agent")
    )
    return _token_response(issued, service.access_expires_in)


@router.get("/invitations/{token}", response_model=InvitationTokenInfo)
async def validate_invitation(
    token: str, db: AsyncSession = Depends(get_db)
) -> InvitationTokenInfo:
    invitation = await AuthService(db).validate_invitation_token(token)
    return InvitationTokenInfo(email=invitation.email)


@router.post("/invitations/{token}/accept", response_model=TokenResponse)
async def accept_invitation(
    token: str,
    body: AcceptInvitationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    service = AuthService(db)
    issued = await service.accept_invitation(
        token, body.full_name, body.password, user_agent=request.headers.get("user-agent")
    )
    return _token_response(issued, service.access_expires_in)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    service = AuthService(db)
    issued = await service.refresh(
        body.refresh_token, user_agent=request.headers.get("user-agent")
    )
    return _token_response(issued, service.access_expires_in)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await AuthService(db).logout(user, body.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_reset(
    body: PasswordResetRequest, request: Request, db: AsyncSession = Depends(get_db)
) -> PasswordResetRequestResponse:
    await AuthService(db).request_password_reset(
        body.email, user_agent=request.headers.get("user-agent")
    )
    # Always the same response, whether or not the email exists (RN-41).
    return PasswordResetRequestResponse(message=_RESET_REQUEST_MESSAGE)


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    body: PasswordResetConfirm, db: AsyncSession = Depends(get_db)
) -> Response:
    await AuthService(db).confirm_password_reset(body.token, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeRead)
async def read_me(user: User = Depends(get_current_user)) -> MeRead:
    return MeRead.model_validate(user)


@router.patch("/me", response_model=MeRead)
async def update_me(
    body: UpdateMeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeRead:
    updated = await UsersService(db).update_own_name(user, body.full_name)
    return MeRead.model_validate(updated)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    await AuthService(db).change_password(user, body.current_password, body.new_password)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
