"""
Casos de uso (comandos) para autenticación.
"""

import logging
from dataclasses import dataclass

from application.auth.token_manager_interface import ITokenManager
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import InvalidCredentials

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoginCredentials:
    """Datos de entrada del caso de uso de login."""

    username: str
    password: str


@dataclass(frozen=True)
class LoginResult:
    """Resultado del login autenticado."""

    access_token: str
    refresh_token: str


class LoginUseCase:
    """Autentica un usuario y emite un token de acceso."""

    def __init__(
        self,
        user_repository: IUserRepository,
        token_manager: ITokenManager,
        password_verifier: IPasswordManager,
    ) -> None:
        self._user_repository = user_repository
        self._token_manager = token_manager
        self._password_verifier = password_verifier

    def execute(self, credentials: LoginCredentials) -> LoginResult:
        user = self._user_repository.get_by_username(credentials.username)

        if user is None:
            logger.warning("Usuario no encontrado")
            raise InvalidCredentials()

        if not self._password_verifier.verify(credentials.password, user.password):
            logger.warning("Contraseña inválida")
            raise InvalidCredentials()

        claims = {
            "username": user.username,
            "role": user.role,
            "ver": user.token_version,
        }
        access_token = self._token_manager.create_access_token(
            subject=str(user.id),
            claims=claims,
        )
        refresh_token = self._token_manager.create_refresh_token(
            subject=str(user.id),
            token_version=user.token_version,
        )

        return LoginResult(access_token=access_token, refresh_token=refresh_token)
