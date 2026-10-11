"""
Unit tests — caso de uso de logout.
"""

from unittest.mock import MagicMock

import pytest

from application.auth.logout_use_case import LogoutCommand, LogoutUseCase
from application.shared.user_repository_interface import IUserRepository
from domain.exceptions import UserNotFound
from tests.helpers import make_user

pytestmark = pytest.mark.unit


class TestLogoutUseCase:
    def test_bumps_token_version_for_authenticated_user(self):
        user_repository = MagicMock(spec=IUserRepository)
        user_repository.get_by_id.return_value = make_user(id=7)

        LogoutUseCase(user_repository).execute(LogoutCommand(user_id=7))

        user_repository.bump_token_version.assert_called_once_with(7)

    def test_unknown_user_raises_user_not_found(self):
        user_repository = MagicMock(spec=IUserRepository)
        user_repository.get_by_id.return_value = None

        with pytest.raises(UserNotFound):
            LogoutUseCase(user_repository).execute(LogoutCommand(user_id=99))

        user_repository.bump_token_version.assert_not_called()
