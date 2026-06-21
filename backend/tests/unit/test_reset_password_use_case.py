"""
Unit tests — caso de uso de restablecimiento de contraseña.

El repositorio, el verificador de password y el manager de tokens se sustituyen por mocks.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.auth.reset_password_use_case import ResetPasswordCommand, ResetPasswordUseCase
from application.auth.token_manager_interface import ITokenManager
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.auth.token_payload_entity import TokenPayload
from domain.exceptions import DomainValidationError, UserNotFound
from tests.helpers import make_user

pytestmark = pytest.mark.unit


def _reset_payload(subject: str = "1") -> TokenPayload:
    return TokenPayload(subject=subject, expires_at=datetime.now(UTC))


class TestResetPasswordUseCase:
    def test_valid_token_updates_password_without_issuing_session(self):
        user_repository = MagicMock(spec=IUserRepository)
        password_manager = MagicMock(spec=IPasswordManager)
        token_manager = MagicMock(spec=ITokenManager)
        user = make_user()
        user_repository.get_by_id.return_value = user
        token_manager.decode_reset_token.return_value = _reset_payload("1")
        password_manager.hash.return_value = "hashed-new-password"

        result = ResetPasswordUseCase(user_repository, token_manager, password_manager).execute(
            ResetPasswordCommand(reset_token="reset-token", new_password="nueva123")
        )

        # No se auto-loguea: no se emiten tokens de sesión.
        assert result is None
        password_manager.hash.assert_called_once_with("nueva123")
        assert user.password == "hashed-new-password"
        user_repository.update_user.assert_called_once_with(user)
        token_manager.create_access_token.assert_not_called()
        token_manager.create_refresh_token.assert_not_called()

    def test_too_short_password_raises_validation_error(self):
        user_repository = MagicMock(spec=IUserRepository)
        password_manager = MagicMock(spec=IPasswordManager)
        token_manager = MagicMock(spec=ITokenManager)

        with pytest.raises(DomainValidationError):
            ResetPasswordUseCase(user_repository, token_manager, password_manager).execute(
                ResetPasswordCommand(reset_token="reset-token", new_password="123")
            )

        token_manager.decode_reset_token.assert_not_called()
        user_repository.update_user.assert_not_called()

    def test_unknown_user_raises_user_not_found(self):
        user_repository = MagicMock(spec=IUserRepository)
        password_manager = MagicMock(spec=IPasswordManager)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_reset_token.return_value = _reset_payload("99")
        user_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            ResetPasswordUseCase(user_repository, token_manager, password_manager).execute(
                ResetPasswordCommand(reset_token="reset-token", new_password="nueva123")
            )

        user_repository.update_user.assert_not_called()
        token_manager.create_access_token.assert_not_called()
