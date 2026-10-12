"""
Unit tests — dependencias de autenticación y cambio de contraseña obligatorio.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from api.dependencies import (
    get_authenticated_user,
    get_current_user,
    get_current_user_allowing_password_change,
)
from application.auth.token_manager_interface import ITokenManager
from application.shared.user_repository_interface import IUserRepository
from domain.auth.token_payload_entity import TokenPayload
from domain.exceptions import InvalidToken, PasswordChangeRequired
from tests.helpers import make_user

pytestmark = pytest.mark.unit


def _credentials(token: str = "access-token"):
    return MagicMock(credentials=token)


def _payload(subject: str = "1", version: int = 0) -> TokenPayload:
    return TokenPayload(
        subject=subject,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
        token_version=version,
    )


class TestGetAuthenticatedUser:
    def test_returns_user_even_when_must_change_password(self):
        token_manager = MagicMock(spec=ITokenManager)
        user_repository = MagicMock(spec=IUserRepository)
        token_manager.decode_access_token.return_value = _payload()
        user = make_user(must_change_password=True)
        user_repository.get_by_id.return_value = user

        result = get_authenticated_user(
            credentials=_credentials(),
            token_manager=token_manager,
            user_repository=user_repository,
        )

        assert result is user

    def test_missing_credentials_raises_invalid_token(self):
        with pytest.raises(InvalidToken, match="no proporcionado"):
            get_authenticated_user(
                credentials=None,
                token_manager=MagicMock(spec=ITokenManager),
                user_repository=MagicMock(spec=IUserRepository),
            )


class TestGetCurrentUser:
    def test_blocks_user_with_must_change_password(self):
        user = make_user(must_change_password=True)

        with pytest.raises(PasswordChangeRequired):
            get_current_user(user=user)

    def test_allows_user_without_pending_change(self):
        user = make_user(must_change_password=False)

        assert get_current_user(user=user) is user


class TestGetCurrentUserAllowingPasswordChange:
    def test_allows_user_with_must_change_password(self):
        user = make_user(must_change_password=True)

        assert get_current_user_allowing_password_change(user=user) is user
