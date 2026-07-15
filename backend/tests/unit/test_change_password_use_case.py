"""
Unit tests — caso de uso de cambio de contraseña del usuario autenticado.

El repositorio y el gestor de contraseñas se sustituyen por mocks para aislar
las reglas de negocio.
"""

from unittest.mock import MagicMock

import pytest

from application.auth.change_password_use_case import (
    ChangePasswordCommand,
    ChangePasswordUseCase,
)
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import DomainValidationError, UserNotFound
from tests.helpers import make_user

pytestmark = pytest.mark.unit


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock(spec=IUserRepository)


@pytest.fixture
def password_manager() -> MagicMock:
    return MagicMock(spec=IPasswordManager)


class TestChangePasswordUseCase:
    def test_valid_change_updates_password_without_invalidating_session(
        self, user_repository, password_manager
    ):
        user = make_user(id=1, password="stored-hash")
        user_repository.get_by_id.return_value = user
        # verify(actual) -> True; verify(nueva == actual) -> False
        password_manager.verify.side_effect = [True, False]
        password_manager.hash.return_value = "hashed-new-password"

        result = ChangePasswordUseCase(user_repository, password_manager).execute(
            ChangePasswordCommand(user_id=1, current_password="actual123", new_password="nueva123")
        )

        assert result is None
        password_manager.hash.assert_called_once_with("nueva123")
        assert user.password == "hashed-new-password"
        user_repository.update_user.assert_called_once_with(user)
        # La sesión en curso se mantiene válida: no se incrementa la versión de token.
        user_repository.bump_token_version.assert_not_called()

    def test_too_short_password_raises_validation_error(self, user_repository, password_manager):
        with pytest.raises(DomainValidationError):
            ChangePasswordUseCase(user_repository, password_manager).execute(
                ChangePasswordCommand(user_id=1, current_password="actual123", new_password="123")
            )

        user_repository.get_by_id.assert_not_called()
        user_repository.update_user.assert_not_called()

    def test_unknown_user_raises_user_not_found(self, user_repository, password_manager):
        user_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            ChangePasswordUseCase(user_repository, password_manager).execute(
                ChangePasswordCommand(
                    user_id=404, current_password="actual123", new_password="nueva123"
                )
            )

        user_repository.update_user.assert_not_called()

    def test_wrong_current_password_raises_validation_error(
        self, user_repository, password_manager
    ):
        user_repository.get_by_id.return_value = make_user(id=1, password="stored-hash")
        password_manager.verify.return_value = False

        with pytest.raises(DomainValidationError, match="actual"):
            ChangePasswordUseCase(user_repository, password_manager).execute(
                ChangePasswordCommand(
                    user_id=1, current_password="incorrecta", new_password="nueva123"
                )
            )

        password_manager.hash.assert_not_called()
        user_repository.update_user.assert_not_called()

    def test_new_password_equal_to_current_raises_validation_error(
        self, user_repository, password_manager
    ):
        user_repository.get_by_id.return_value = make_user(id=1, password="stored-hash")
        # verify(actual) -> True; verify(nueva == actual) -> True
        password_manager.verify.side_effect = [True, True]

        with pytest.raises(DomainValidationError, match="distinta"):
            ChangePasswordUseCase(user_repository, password_manager).execute(
                ChangePasswordCommand(
                    user_id=1, current_password="actual123", new_password="actual123"
                )
            )

        password_manager.hash.assert_not_called()
        user_repository.update_user.assert_not_called()
