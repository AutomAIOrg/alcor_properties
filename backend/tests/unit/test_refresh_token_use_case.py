"""
Unit tests — caso de uso para renovar access tokens.

El repositorio y el manager de tokens se sustituyen por mocks.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from application.auth.refresh_token_use_case import (
    RefreshTokenCommand,
    RefreshTokenUseCase,
)
from application.auth.token_manager_interface import ITokenManager
from application.shared.user_repository_interface import IUserRepository
from domain.auth.token_payload_entity import TokenPayload
from domain.auth.user_entity import Role
from domain.exceptions import InvalidToken
from tests.helpers import make_user

pytestmark = pytest.mark.unit


class TestRefreshTokenUseCase:
    def test_valid_refresh_token_creates_new_access_token_with_current_user_claims(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(subject="1")
        user_repository.get_by_id.return_value = make_user()
        token_manager.create_access_token.return_value = "new-access-token"

        result = RefreshTokenUseCase(user_repository, token_manager).execute(
            RefreshTokenCommand(refresh_token="refresh-token")
        )

        assert result.access_token == "new-access-token"
        token_manager.decode_refresh_token.assert_called_once_with("refresh-token")
        user_repository.get_by_id.assert_called_once_with(1)
        token_manager.create_access_token.assert_called_once_with(
            subject="1",
            claims={"username": "admin", "role": Role.ADMIN},
        )

    def test_missing_user_raises_invalid_token(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(subject="99")
        user_repository.get_by_id.return_value = None

        with pytest.raises(InvalidToken, match="Usuario del token no encontrado"):
            RefreshTokenUseCase(user_repository, token_manager).execute(
                RefreshTokenCommand(refresh_token="refresh-token")
            )

        token_manager.create_access_token.assert_not_called()

    def test_invalid_subject_raises_invalid_token(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(subject="not-an-int")

        with pytest.raises(InvalidToken, match="sujeto inválido"):
            RefreshTokenUseCase(user_repository, token_manager).execute(
                RefreshTokenCommand(refresh_token="refresh-token")
            )

        user_repository.get_by_id.assert_not_called()
        token_manager.create_access_token.assert_not_called()


def _token_payload(subject: str) -> TokenPayload:
    return TokenPayload(
        subject=subject,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
