"""
Caso de uso para cerrar sesión invalidando tokens en el servidor.
"""

from dataclasses import dataclass

from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import UserNotFound


@dataclass(frozen=True)
class LogoutCommand:
    """Datos de entrada del caso de uso de logout."""

    user_id: int


class LogoutUseCase:
    """Invalida las sesiones activas del usuario autenticado."""

    def __init__(self, user_repository: IUserRepository) -> None:
        self._user_repository = user_repository

    def execute(self, command: LogoutCommand) -> None:
        user = self._user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFound()
        self._user_repository.bump_token_version(command.user_id)
