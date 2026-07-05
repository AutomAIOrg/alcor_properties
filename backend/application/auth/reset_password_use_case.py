"""
Caso de uso para restablecer la contraseña.

A partir de un token de restablecimiento válido, fija la nueva contraseña del
usuario. No emite tokens de sesión: tras el cambio, el usuario debe iniciar sesión
con su nueva contraseña.
"""

import logging
from dataclasses import dataclass

from application.auth.token_manager_interface import ITokenManager
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import DomainValidationError, InvalidToken, UserNotFound

logger = logging.getLogger(__name__)

MIN_PASSWORD_LENGTH = 6


@dataclass(frozen=True)
class ResetPasswordCommand:
    """Datos de entrada del caso de uso de restablecimiento de contraseña."""

    reset_token: str
    new_password: str


class ResetPasswordUseCase:
    """Valida el token de restablecimiento y fija la nueva contraseña."""

    def __init__(
        self,
        user_repository: IUserRepository,
        token_manager: ITokenManager,
        password_manager: IPasswordManager,
    ) -> None:
        self._user_repository = user_repository
        self._token_manager = token_manager
        self._password_manager = password_manager

    def execute(self, command: ResetPasswordCommand) -> None:
        if len(command.new_password) < MIN_PASSWORD_LENGTH:
            raise DomainValidationError(
                f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres"
            )

        payload = self._token_manager.decode_reset_token(command.reset_token)

        if not payload.jti:
            logger.warning("Token de restablecimiento sin jti")
            raise InvalidToken("Token de restablecimiento inválido.")

        try:
            user_id = int(payload.subject)
        except (TypeError, ValueError) as exc:
            logger.warning("Subject del token de restablecimiento no válido")
            raise InvalidToken("Subject del token no válido.") from exc

        if not self._user_repository.consume_password_reset_jti(user_id, payload.jti):
            logger.warning("Token de restablecimiento ya utilizado o inválido")
            raise InvalidToken("Token de restablecimiento ya utilizado o inválido.")

        user = self._user_repository.get_by_id(user_id)
        if user is None:
            raise UserNotFound()

        user.password = self._password_manager.hash(command.new_password)
        self._user_repository.update_user(user)
        logger.info("Contraseña restablecida correctamente")
