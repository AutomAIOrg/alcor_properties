"""
DTOs (Data Transfer Objects) para la API de login.
"""

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    """DTO de entrada para POST /login/."""

    username: str = Field(..., description="Nombre de usuario")
    password: str = Field(..., description="Contraseña")


class LoginResponse(BaseModel):
    """DTO de salida. Modelo de respuesta para la API."""

    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    """DTO de entrada para POST /forgot-password."""

    email: str = Field(..., description="Email del usuario que olvidó la contraseña")


class MessageResponse(BaseModel):
    """DTO de salida genérico con un mensaje informativo."""

    message: str


class ResetPasswordRequest(BaseModel):
    """DTO de entrada para POST /reset-password."""

    reset_token: str = Field(..., description="Token de restablecimiento")
    new_password: str = Field(..., description="Nueva contraseña")


class RefreshTokenRequest(BaseModel):
    """DTO de entrada para POST /refresh."""

    refresh_token: str = Field(..., description="Token de refresh")


class AccessTokenResponse(BaseModel):
    """DTO de salida para renovar access tokens."""

    access_token: str
    token_type: str = "bearer"
