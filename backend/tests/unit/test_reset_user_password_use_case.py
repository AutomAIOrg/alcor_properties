"""
Unit tests — caso de uso de restablecimiento de la contraseña de un usuario a la
contraseña inicial (acción de administrador).

El repositorio y el gestor de contraseñas se sustituyen por mocks.
"""

from unittest.mock import MagicMock

import pytest

from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from application.users.reset_user_password_use_case import (
    ResetUserPasswordCommand,
    ResetUserPasswordUseCase,
)
from domain.exceptions import UserNotFound
from tests.helpers import make_user

pytestmark = pytest.mark.unit


@pytest.fixture
def user_repository() -> MagicMock:
    return MagicMock(spec=IUserRepository)


@pytest.fixture
def password_manager() -> MagicMock:
    return MagicMock(spec=IPasswordManager)


class TestResetUserPasswordUseCase:
    def test_resets_password_and_invalidates_sessions(self, user_repository, password_manager):
        user = make_user(id=2, password="stored-hash", must_change_password=False)
        user_repository.get_by_id.return_value = user
        password_manager.hash.return_value = "hashed-initial-password"

        result = ResetUserPasswordUseCase(user_repository, password_manager).execute(
            ResetUserPasswordCommand(user_id=2, initial_password="alcor1234")
        )

        assert result is None
        password_manager.hash.assert_called_once_with("alcor1234")
        assert user.password == "hashed-initial-password"
        # Vuelve a tener la contraseña inicial: debe fijar una propia al entrar.
        assert user.must_change_password is True
        user_repository.update_user.assert_called_once_with(user)
        # Invalida las sesiones activas del usuario afectado.
        user_repository.bump_token_version.assert_called_once_with(2)

    def test_unknown_user_raises_user_not_found(self, user_repository, password_manager):
        user_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            ResetUserPasswordUseCase(user_repository, password_manager).execute(
                ResetUserPasswordCommand(user_id=404, initial_password="alcor1234")
            )

        password_manager.hash.assert_not_called()
        user_repository.update_user.assert_not_called()
        user_repository.bump_token_version.assert_not_called()
