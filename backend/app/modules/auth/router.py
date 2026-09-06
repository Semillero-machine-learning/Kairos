"""HTTP endpoints for auth. No business logic or queries live here."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
    UserRead,
)
from app.modules.auth.service import AuthService, IssuedTokens
from app.modules.users.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


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
