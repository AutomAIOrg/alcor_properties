"""
Enrutador de autenticación.
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from api.dependencies import (
    get_change_password_use_case,
    get_current_user,
    get_forgot_password_use_case,
    get_login_use_case,
    get_refresh_token_use_case,
    get_reset_password_use_case,
)
from api.v1.auth.schemas import (
    AccessTokenResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
)
from application.auth.change_password_use_case import ChangePasswordCommand, ChangePasswordUseCase
from application.auth.forgot_password_use_case import ForgotPasswordUseCase
from application.auth.login_use_case import LoginCredentials, LoginUseCase
from application.auth.refresh_token_use_case import RefreshTokenCommand, RefreshTokenUseCase
from application.auth.reset_password_use_case import ResetPasswordCommand, ResetPasswordUseCase
from domain.auth.user_entity import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def user_login(
    request: LoginRequest,
    login_use_case: Annotated[LoginUseCase, Depends(get_login_use_case)],
):
    """Login de usuario."""
    logger.info(f"Login de usuario: {request.username}")
    token = login_use_case.execute(
        LoginCredentials(username=request.username, password=request.password)
    )
    return LoginResponse(
        access_token=token.access_token,
        refresh_token=token.refresh_token,
    )


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    forgot_password_use_case: Annotated[
        ForgotPasswordUseCase, Depends(get_forgot_password_use_case)
    ],
):
    """Si el email está registrado, envía un enlace para restablecer la contraseña."""
    logger.info("Solicitud de restablecimiento de contraseña")
    forgot_password_use_case.execute(request.email)
    # Respuesta uniforme: nunca se revela si el email existe.
    return MessageResponse(
        message="Si el email está registrado, recibirás un enlace para restablecer tu contraseña."
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: ResetPasswordRequest,
    reset_password_use_case: Annotated[ResetPasswordUseCase, Depends(get_reset_password_use_case)],
):
    """Fija la nueva contraseña a partir del token recibido por email."""
    logger.info("Restablecimiento de contraseña")
    reset_password_use_case.execute(
        ResetPasswordCommand(
            reset_token=request.reset_token,
            new_password=request.new_password,
        )
    )
    return MessageResponse(message="Contraseña actualizada. Ya puedes iniciar sesión.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    change_password_use_case: Annotated[
        ChangePasswordUseCase, Depends(get_change_password_use_case)
    ],
):
    """Cambia la contraseña del usuario autenticado, exigiendo la contraseña actual."""
    logger.info("Cambio de contraseña del usuario autenticado")
    change_password_use_case.execute(
        ChangePasswordCommand(
            user_id=current_user.id,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    )
    return MessageResponse(message="Contraseña actualizada correctamente.")


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
