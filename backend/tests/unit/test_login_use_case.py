"""
Unit tests — caso de uso de login.

El repositorio, el verificador de password y el manager de tokens se sustituyen por mocks.
"""

from unittest.mock import MagicMock

import pytest

from application.auth.login_use_case import LoginCredentials, LoginUseCase
from application.auth.token_manager_interface import ITokenManager
from application.shared.password_manager_interface import IPasswordManager
from application.shared.user_repository_interface import IUserRepository
from domain.auth.user_entity import Role
from domain.exceptions import InvalidCredentials
from tests.helpers import make_user

pytestmark = pytest.mark.unit


class TestLoginUseCase:
    def test_valid_credentials_create_token_with_user_claims(self):
        user_repository = MagicMock(spec=IUserRepository)
        password_verifier = MagicMock(spec=IPasswordManager)
        token_manager = MagicMock(spec=ITokenManager)
        user_repository.get_by_username.return_value = make_user()
        password_verifier.verify.return_value = True
        token_manager.create_access_token.return_value = "access-token"
        token_manager.create_refresh_token.return_value = "refresh-token"

        result = LoginUseCase(user_repository, token_manager, password_verifier).execute(
            LoginCredentials(username="admin", password="admin-password")
        )

        assert result.access_token == "access-token"
        assert result.refresh_token == "refresh-token"
        user_repository.get_by_username.assert_called_once_with("admin")
        password_verifier.verify.assert_called_once_with(
            "admin-password", "$2b$12$dummyhashforunitandintegrationtests"
        )
        token_manager.create_access_token.assert_called_once_with(
            subject="1",
            claims={"username": "admin", "role": Role.ADMIN, "ver": 0, "mcp": False},
        )
        token_manager.create_refresh_token.assert_called_once_with(subject="1", token_version=0)

    def test_unknown_username_raises_invalid_credentials(self):
        user_repository = MagicMock(spec=IUserRepository)
        password_verifier = MagicMock(spec=IPasswordManager)
        token_manager = MagicMock(spec=ITokenManager)
        user_repository.get_by_username.return_value = None

        with pytest.raises(InvalidCredentials):
            LoginUseCase(user_repository, token_manager, password_verifier).execute(
                LoginCredentials(username="missing", password="admin-password")
            )

        password_verifier.verify.assert_not_called()
        token_manager.create_access_token.assert_not_called()
        token_manager.create_refresh_token.assert_not_called()

    def test_wrong_password_raises_invalid_credentials(self):
        user_repository = MagicMock(spec=IUserRepository)
        password_verifier = MagicMock(spec=IPasswordManager)
        token_manager = MagicMock(spec=ITokenManager)
        user_repository.get_by_username.return_value = make_user()
        password_verifier.verify.return_value = False

        with pytest.raises(InvalidCredentials):
            LoginUseCase(user_repository, token_manager, password_verifier).execute(
                LoginCredentials(username="admin", password="wrong-password")
            )

        token_manager.create_access_token.assert_not_called()
        token_manager.create_refresh_token.assert_not_called()
