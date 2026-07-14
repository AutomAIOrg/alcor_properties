"""
Caso de uso para que un usuario autenticado cambie su propia contraseña.

Exige la contraseña actual y fija la nueva. No invalida la sesión en curso: el
propio usuario es quien realiza el cambio conociendo ambas contraseñas, por lo
que su sesión sigue siendo válida tras la operación.
"""

import logging
from dataclasses import dataclass

from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import DomainValidationError, UserNotFound

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 6


@dataclass(frozen=True)
class ChangePasswordCommand:
    """Datos de entrada del caso de uso de cambio de contraseña."""

    user_id: int
    current_password: str
    new_password: str


class ChangePasswordUseCase:
    """Verifica la contraseña actual y fija la nueva contraseña del usuario."""

    def __init__(
        self,
        user_repository: IUserRepository,
        password_manager: IPasswordManager,
    ) -> None:
        self._user_repository = user_repository
        self._password_manager = password_manager

    def execute(self, command: ChangePasswordCommand) -> None:
        if len(command.new_password) < MIN_PASSWORD_LENGTH:
            raise DomainValidationError(
                f"La nueva contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres"
            )

        user = self._user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFound()

        if not self._password_manager.verify(command.current_password, user.password):
            logger.warning("Contraseña actual incorrecta al cambiar la contraseña")
            # 422 (no 401): un 401 dispararía el refresh/logout del interceptor del frontend.
            raise DomainValidationError("La contraseña actual no es correcta")

        if self._password_manager.verify(command.new_password, user.password):
            raise DomainValidationError("La nueva contraseña debe ser distinta de la actual")

        user.password = self._password_manager.hash(command.new_password)
        self._user_repository.update_user(user)
        logger.info("Contraseña cambiada correctamente")
