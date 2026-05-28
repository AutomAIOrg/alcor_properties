"""
Enrutador de autenticación.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import get_login_use_case, get_refresh_token_use_case
from api.v1.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
)
from application.auth.login_use_case import LoginCredentials, LoginUseCase
from application.auth.refresh_token_use_case import RefreshTokenCommand, RefreshTokenUseCase

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def user_login(
    request: LoginRequest,
    login_use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
):
    """Login de usuario."""
    token = login_use_case.execute(
        LoginCredentials(username=request.username, password=request.password)
    )
    return LoginResponse(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_access_token(
    request: RefreshTokenRequest,
    refresh_token_use_case: Annotated[RefreshTokenUseCase, Depends(get_refresh_token_use_case)],
):
    """Renueva el access token a partir de un refresh token válido."""
    result = refresh_token_use_case.execute(
        RefreshTokenCommand(refresh_token=request.refresh_token)
    )
    return AccessTokenResponse(access_token=result.access_token)
