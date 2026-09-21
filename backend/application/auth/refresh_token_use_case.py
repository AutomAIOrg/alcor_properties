"""
Caso de uso para renovar tokens de acceso con rotación de refresh.
"""

import logging
from dataclasses import dataclass

from application.auth.token_manager_interface import ITokenManager
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import InvalidToken

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RefreshTokenCommand:
    """Datos de entrada del caso de uso de refresh."""

    refresh_token: str


@dataclass(frozen=True)
class RefreshTokenResult:
    """Resultado de renovar access y refresh tokens."""

    access_token: str
    refresh_token: str


class RefreshTokenUseCase:
    """Valida un refresh token, lo rota e invalida el anterior."""

    def __init__(
        self,
        user_repository: IUserRepository,
        token_manager: ITokenManager,
    ) -> None:
        self._user_repository = user_repository
        self._token_manager = token_manager

    def execute(self, command: RefreshTokenCommand) -> RefreshTokenResult:
        token_payload = self._token_manager.decode_refresh_token(command.refresh_token)

        try:
            user_id = int(token_payload.subject)
        except (TypeError, ValueError) as exc:
            raise InvalidToken("Token con sujeto inválido") from exc

        if not token_payload.jti or not token_payload.session_id:
            raise InvalidToken("Refresh token sin identificador")

        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise InvalidToken("Usuario del token no encontrado")

        if (token_payload.token_version or 0) != user.token_version:
            raise InvalidToken("Token de sesión revocado")

        issued_refresh = self._token_manager.create_refresh_token(
            subject=str(user.id),
            token_version=user.token_version,
            session_id=token_payload.session_id,
        )
        rotated = self._user_repository.rotate_auth_session(
            user.id,
            token_payload.session_id,
            token_payload.jti,
            issued_refresh.jti,
            issued_refresh.expires_at,
            user.token_version,
        )
        if not rotated:
            # El jti presentado no es el activo: reutilización o carrera → revocar sesión.
            logger.warning(
                "Reutilización de refresh token detectada para el usuario %s; sesión revocada",
                user.id,
            )
            raise InvalidToken("Reutilización de refresh token detectada")

        access_token = self._token_manager.create_access_token(
            subject=str(user.id),
            claims={
                "sid": token_payload.session_id,
                "username": user.username,
                "role": user.role,
                "ver": user.token_version,
                "mcp": user.must_change_password,
            },
        )
        return RefreshTokenResult(
            access_token=access_token,
            refresh_token=issued_refresh.token,
        )
