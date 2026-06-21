"""
Implementación JWT del puerto de tokens.
"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from application.auth.token_manager_interface import ITokenManager
from config import settings
from domain.auth.token_payload_entity import TokenPayload
from domain.auth.user_entity import Role
from domain.exceptions import InvalidToken, TokenExpired


class JwtTokenManager(ITokenManager):
    """Emite y valida tokens JWT firmados con la configuración de la aplicación."""

    def __init__(
        self,
        secret_key: str | None = None,
        algorithm: str | None = None,
        access_token_expire_minutes: int | None = None,
        refresh_token_expire_days: int | None = None,
        reset_token_expire_minutes: int = 15,
    ) -> None:
        self._secret_key = secret_key or settings.JWT_SECRET_KEY
        self._algorithm = algorithm or settings.JWT_ALGORITHM
        self._access_token_expire_minutes = (
            access_token_expire_minutes
            if access_token_expire_minutes is not None
            else settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
        self._refresh_token_expire_days = (
            refresh_token_expire_days
            if refresh_token_expire_days is not None
            else settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        self._reset_token_expire_minutes = reset_token_expire_minutes

        if not self._secret_key:
            raise ValueError("JWT_SECRET_KEY debe estar configurado")

    def create_access_token(
        self,
        subject: str,
        claims: Mapping[str, Any] | None = None,
    ) -> str:
        """Crea un token de acceso para un sujeto autenticado."""
        return self._create_token(
            subject=subject,
            token_type="access",
            expires_delta=timedelta(minutes=self._access_token_expire_minutes),
            claims=claims,
        )

    def decode_access_token(self, token: str) -> TokenPayload:
        """Valida un token de acceso y devuelve sus claims normalizados."""
        return self._decode_token(token, expected_type="access")

    def create_refresh_token(self, subject: str) -> str:
        """Crea un token de refresh para un sujeto autenticado."""
        return self._create_token(
            subject=subject,
            token_type="refresh",
            expires_delta=timedelta(days=self._refresh_token_expire_days),
        )

    def decode_refresh_token(self, token: str) -> TokenPayload:
        """Valida un token de refresh y devuelve sus claims normalizados."""
        return self._decode_token(token, expected_type="refresh")

    def create_reset_token(self, subject: str) -> str:
        """Crea un token de un solo uso para restablecer la contraseña."""
        return self._create_token(
            subject=subject,
            token_type="reset",
            expires_delta=timedelta(minutes=self._reset_token_expire_minutes),
        )

    def decode_reset_token(self, token: str) -> TokenPayload:
        """Valida un token de restablecimiento de contraseña y devuelve sus claims."""
        return self._decode_token(token, expected_type="reset")

    def _create_token(
        self,
        subject: str,
        token_type: str,
        expires_delta: timedelta,
        claims: Mapping[str, Any] | None = None,
    ) -> str:
        now = datetime.now(UTC)
        expires_at = now + expires_delta

        payload: dict[str, Any] = dict(claims or {})
        if isinstance(payload.get("role"), Role):
            payload["role"] = payload["role"].value

        payload.update(
            {
                "sub": subject,
                "type": token_type,
                "iat": int(now.timestamp()),
                "exp": int(expires_at.timestamp()),
            }
        )

        return jwt.encode(payload, self._secret_key, algorithm=self._algorithm)

    def _decode_token(self, token: str, expected_type: str) -> TokenPayload:
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                options={"require": ["sub", "type", "exp", "iat"]},
            )
        except ExpiredSignatureError as exc:
            raise TokenExpired() from exc
        except InvalidTokenError as exc:
            raise InvalidToken() from exc

        if payload["type"] != expected_type:
            raise InvalidToken("Token con tipo inválido")

        try:
            role = Role(payload["role"]) if payload.get("role") else None
        except ValueError as exc:
            raise InvalidToken("Token con rol inválido") from exc

        return TokenPayload(
            subject=payload["sub"],
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
            username=payload.get("username"),
            role=role,
        )
