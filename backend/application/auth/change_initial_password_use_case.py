"""
Caso de uso para que un usuario con la contraseña inicial del sistema fije la suya.

Se aplica al primer acceso tras el alta y tras un restablecimiento del administrador.
No exige la contraseña actual: el usuario ya está autenticado con la contraseña
inicial y el objetivo es precisamente que deje de usarla.

Invalida las sesiones abiertas con la contraseña inicial y emite tokens nuevos, de
modo que quien realiza el cambio continúa sin volver a iniciar sesión.
"""

import logging
from dataclasses import dataclass

from application.auth.token_manager_interface import ITokenManager
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import DomainValidationError, UserNotFound

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 6


@dataclass(frozen=True)
class ChangeInitialPasswordCommand:
    """Datos de entrada del caso de uso de cambio de la contraseña inicial."""

    user_id: int
    new_password: str


@dataclass(frozen=True)
class ChangeInitialPasswordResult:
    """Tokens de sesión emitidos tras fijar la nueva contraseña."""

    access_token: str
    refresh_token: str


class ChangeInitialPasswordUseCase:
    """Fija la contraseña propia de un usuario que aún tiene la inicial del sistema."""

    def __init__(
        self,
        user_repository: IUserRepository,
        password_manager: IPasswordManager,
        token_manager: ITokenManager,
    ) -> None:
        self._user_repository = user_repository
        self._password_manager = password_manager
        self._token_manager = token_manager

    def execute(self, command: ChangeInitialPasswordCommand) -> ChangeInitialPasswordResult:
        user = self._user_repository.get_by_id(command.user_id)
        if user is None:
            raise UserNotFound()

        if not user.must_change_password:
            # 422 (no 401): un 401 dispararía el refresh/logout del interceptor del frontend.
            raise DomainValidationError("El usuario ya tiene una contraseña propia")

        if len(command.new_password) < MIN_PASSWORD_LENGTH:
            raise DomainValidationError(
                f"La nueva contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres"
            )

        if self._password_manager.verify(command.new_password, user.password):
            raise DomainValidationError("La nueva contraseña debe ser distinta de la inicial")

        user.password = self._password_manager.hash(command.new_password)
        user.must_change_password = False
        self._user_repository.update_user(user)

        # Invalida las sesiones abiertas con la contraseña inicial.
        self._user_repository.bump_token_version(user.id)
        updated_user = self._user_repository.get_by_id(user.id)
        if updated_user is None:
            raise UserNotFound()

        access_token = self._token_manager.create_access_token(
            subject=str(updated_user.id),
            claims={
                "username": updated_user.username,
                "role": updated_user.role,
                "ver": updated_user.token_version,
                "mcp": updated_user.must_change_password,
            },
        )
        refresh_token = self._token_manager.create_refresh_token(
            subject=str(updated_user.id),
            token_version=updated_user.token_version,
        )

        logger.info(f"El usuario {user.id} ha fijado su contraseña inicial")
        return ChangeInitialPasswordResult(
            access_token=access_token,
            refresh_token=refresh_token,
        )
