"""
Caso de uso para que un administrador restablezca la contraseña de un usuario a
la contraseña inicial del sistema.

Pensado como salvavidas: si un usuario pierde su contraseña, el administrador la
devuelve al valor inicial y el usuario reinicia el proceso. Invalida las sesiones
activas del usuario afectado (bump de token_version).
"""

import logging
from dataclasses import dataclass

from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import UserNotFound

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResetUserPasswordCommand:
    """Datos de entrada del caso de uso de restablecimiento a la contraseña inicial."""

    user_id: int
    initial_password: str


class ResetUserPasswordUseCase:
    """Restablece la contraseña de un usuario a la contraseña inicial del sistema."""

    def __init__(
        self,
        user_repository: IUserRepository,
        password_manager: IPasswordManager,
    ) -> None:
        self._user_repository = user_repository
        self._password_manager = password_manager

    def execute(self, command: ResetUserPasswordCommand) -> None:
        user = self._user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFound()

        user.password = self._password_manager.hash(command.initial_password)
        self._user_repository.update_user(user)
        # Invalida cualquier sesión activa del usuario afectado.
        self._user_repository.bump_token_version(command.user_id)
        logger.info(f"Contraseña del usuario {command.user_id} restablecida a la inicial")
