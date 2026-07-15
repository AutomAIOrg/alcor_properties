"""
Unit tests — caso de uso de cambio de la contraseña inicial del sistema.

El repositorio, el gestor de contraseñas y el de tokens se sustituyen por mocks
para aislar las reglas de negocio.
"""

from unittest.mock import MagicMock

import pytest

from application.auth.change_initial_password_use_case import (
    ChangeInitialPasswordCommand,
    ChangeInitialPasswordUseCase,
)
from application.auth.token_manager_interface import ITokenManager
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.auth.user_entity import Role
from domain.exceptions import DomainValidationError, UserNotFound
from tests.helpers import make_user

pytestmark = pytest.mark.unit


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock(spec=IUserRepository)


@pytest.fixture
def password_manager() -> MagicMock:
    return MagicMock(spec=IPasswordManager)


@pytest.fixture
def token_manager() -> MagicMock:
    manager = MagicMock(spec=ITokenManager)
    manager.create_access_token.return_value = "new-access-token"
    manager.create_refresh_token.return_value = "new-refresh-token"
    return manager


class TestChangeInitialPasswordUseCase:
    def test_valid_change_clears_flag_invalidates_sessions_and_issues_tokens(
        self, user_repository, password_manager, token_manager
    ):
        user = make_user(id=1, password="initial-hash", must_change_password=True)
        # Tras el bump, el repositorio devuelve el usuario ya con la versión nueva.
        updated_user = make_user(
            id=1, password="hashed-new-password", must_change_password=False, token_version=1
        )
        user_repository.get_by_id.side_effect = [user, updated_user]
        # La nueva contraseña no coincide con la inicial almacenada.
        password_manager.verify.return_value = False
        password_manager.hash.return_value = "hashed-new-password"

        result = ChangeInitialPasswordUseCase(
            user_repository, password_manager, token_manager
        ).execute(ChangeInitialPasswordCommand(user_id=1, new_password="nueva123"))

        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"
        password_manager.hash.assert_called_once_with("nueva123")
        assert user.password == "hashed-new-password"
        assert user.must_change_password is False
        user_repository.update_user.assert_called_once_with(user)
        # Las sesiones abiertas con la contraseña inicial dejan de ser válidas.
        user_repository.bump_token_version.assert_called_once_with(1)
        # Los tokens emitidos ya no arrastran la marca de cambio obligatorio.
        token_manager.create_access_token.assert_called_once_with(
            subject="1",
            claims={"username": "admin", "role": Role.ADMIN, "ver": 1, "mcp": False},
        )
        token_manager.create_refresh_token.assert_called_once_with(subject="1", token_version=1)

    def test_user_without_pending_change_raises_validation_error(
        self, user_repository, password_manager, token_manager
    ):
        user_repository.get_by_id.return_value = make_user(id=1, must_change_password=False)

        with pytest.raises(DomainValidationError):
            ChangeInitialPasswordUseCase(user_repository, password_manager, token_manager).execute(
                ChangeInitialPasswordCommand(user_id=1, new_password="nueva123")
            )

        user_repository.update_user.assert_not_called()
        token_manager.create_access_token.assert_not_called()

    def test_too_short_password_raises_validation_error(
        self, user_repository, password_manager, token_manager
    ):
        user_repository.get_by_id.return_value = make_user(id=1, must_change_password=True)

        with pytest.raises(DomainValidationError):
            ChangeInitialPasswordUseCase(user_repository, password_manager, token_manager).execute(
                ChangeInitialPasswordCommand(user_id=1, new_password="123")
            )

        user_repository.update_user.assert_not_called()

    def test_new_password_equal_to_initial_raises_validation_error(
        self, user_repository, password_manager, token_manager
    ):
        user_repository.get_by_id.return_value = make_user(id=1, must_change_password=True)
        password_manager.verify.return_value = True

        with pytest.raises(DomainValidationError, match="distinta"):
            ChangeInitialPasswordUseCase(user_repository, password_manager, token_manager).execute(
                ChangeInitialPasswordCommand(user_id=1, new_password="alcor1234")
            )

        password_manager.hash.assert_not_called()
        user_repository.update_user.assert_not_called()

    def test_unknown_user_raises_user_not_found(
        self, user_repository, password_manager, token_manager
    ):
        user_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            ChangeInitialPasswordUseCase(user_repository, password_manager, token_manager).execute(
                ChangeInitialPasswordCommand(user_id=404, new_password="nueva123")
            )

        user_repository.update_user.assert_not_called()
