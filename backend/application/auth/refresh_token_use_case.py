"""
Caso de uso para renovar tokens de acceso.
"""

from dataclasses import dataclass

from application.auth.token_manager_interface import ITokenManager
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import InvalidToken


@dataclass(frozen=True)
class RefreshTokenCommand:
    """Datos de entrada del caso de uso de refresh."""

    refresh_token: str


@dataclass(frozen=True)
class RefreshTokenResult:
    """Resultado de renovar un access token."""

    access_token: str


class RefreshTokenUseCase:
    """Valida un refresh token y emite un nuevo access token."""

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
        except ValueError as exc:
            raise InvalidToken("Token con sujeto inválido") from exc

        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise InvalidToken("Usuario del token no encontrado")

        access_token = self._token_manager.create_access_token(
            subject=str(user.id),
            claims={
                "username": user.username,
                "role": user.role,
            },
        )
        return RefreshTokenResult(access_token=access_token)
