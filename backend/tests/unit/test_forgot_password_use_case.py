"""
Unit tests — caso de uso de inicio de restablecimiento de contraseña.

El repositorio, el manager de tokens y el emisor de email se sustituyen por mocks.
"""

from unittest.mock import MagicMock

import pytest

from application.auth.forgot_password_use_case import ForgotPasswordUseCase
from application.auth.token_manager_interface import ITokenManager
from application.shared.email_sender_interface import IEmailSender
from application.shared.user_repository_interface import IUserRepository
from tests.helpers import make_user

pytestmark = pytest.mark.unit

FRONTEND_URL = "https://app.example.com"


class TestForgotPasswordUseCase:
    def test_known_email_sends_reset_link(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        email_sender = MagicMock(spec=IEmailSender)
        user = make_user()
        user.email = "admin@example.com"
        user_repository.get_by_email.return_value = user
        token_manager.create_reset_token.return_value = "reset-token"

        result = ForgotPasswordUseCase(
            user_repository, token_manager, email_sender, FRONTEND_URL
        ).execute("admin@example.com")

        assert result is None
        user_repository.get_by_email.assert_called_once_with("admin@example.com")
        token_manager.create_reset_token.assert_called_once_with(subject="1")
        email_sender.send_password_reset.assert_called_once_with(
            "admin@example.com",
            "https://app.example.com/reset-password?token=reset-token",
        )

    def test_email_send_failure_does_not_propagate(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        email_sender = MagicMock(spec=IEmailSender)
        user = make_user()
        user.email = "admin@example.com"
        user_repository.get_by_email.return_value = user
        token_manager.create_reset_token.return_value = "reset-token"
        email_sender.send_password_reset.side_effect = RuntimeError("SMTP caído")

        # Un fallo de envío no debe propagarse (la respuesta sigue siendo uniforme).
        result = ForgotPasswordUseCase(
            user_repository, token_manager, email_sender, FRONTEND_URL
        ).execute("admin@example.com")

        assert result is None
        email_sender.send_password_reset.assert_called_once()

    def test_unknown_email_does_nothing_without_revealing(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        email_sender = MagicMock(spec=IEmailSender)
        user_repository.get_by_email.return_value = None

        result = ForgotPasswordUseCase(
            user_repository, token_manager, email_sender, FRONTEND_URL
        ).execute("missing@example.com")

        # No se lanza excepción (respuesta uniforme) y no se emite token ni email.
        assert result is None
        token_manager.create_reset_token.assert_not_called()
        email_sender.send_password_reset.assert_not_called()
