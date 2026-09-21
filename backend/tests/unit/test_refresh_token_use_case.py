"""
Unit tests — caso de uso para renovar access tokens con rotación de refresh.

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
from domain.auth.issued_refresh_token import IssuedRefreshToken
from domain.auth.token_payload_entity import TokenPayload
from domain.auth.user_entity import Role
from domain.exceptions import InvalidToken
from tests.helpers import make_user

pytestmark = pytest.mark.unit


class TestRefreshTokenUseCase:
    def test_valid_refresh_token_rotates_and_returns_new_pair(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(subject="1", jti="old-jti")
        user_repository.get_by_id.return_value = make_user()
        token_manager.create_refresh_token.return_value = IssuedRefreshToken(
            token="new-refresh-token", jti="new-jti"
        )
        user_repository.rotate_auth_session.return_value = True
        token_manager.create_access_token.return_value = "new-access-token"

        result = RefreshTokenUseCase(user_repository, token_manager).execute(
            RefreshTokenCommand(refresh_token="refresh-token")
        )

        assert result.access_token == "new-access-token"
        assert result.refresh_token == "new-refresh-token"
        user_repository.rotate_auth_session.assert_called_once_with(
            1, "session-id", "old-jti", "new-jti", None, 0
        )
        token_manager.create_access_token.assert_called_once_with(
            subject="1",
            claims={
                "sid": "session-id",
                "username": "admin",
                "role": Role.ADMIN,
                "ver": 0,
                "mcp": False,
            },
        )
        user_repository.bump_token_version.assert_not_called()

    def test_reuse_of_refresh_token_revokes_session(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(
            subject="1", jti="stolen-jti"
        )
        user_repository.get_by_id.return_value = make_user()
        token_manager.create_refresh_token.return_value = IssuedRefreshToken(
            token="ignored", jti="new-jti"
        )
        user_repository.rotate_auth_session.return_value = False

        with pytest.raises(InvalidToken, match="Reutilización"):
            RefreshTokenUseCase(user_repository, token_manager).execute(
                RefreshTokenCommand(refresh_token="refresh-token")
            )

        user_repository.bump_token_version.assert_not_called()
        token_manager.create_access_token.assert_not_called()

    def test_revoked_token_version_raises_invalid_token(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(
            subject="1", version=0, jti="jti"
        )
        user_repository.get_by_id.return_value = make_user(token_version=1)

        with pytest.raises(InvalidToken, match="revocado"):
            RefreshTokenUseCase(user_repository, token_manager).execute(
                RefreshTokenCommand(refresh_token="refresh-token")
            )

        token_manager.create_access_token.assert_not_called()
        user_repository.rotate_auth_session.assert_not_called()

    def test_missing_jti_raises_invalid_token(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(subject="1", jti=None)

        with pytest.raises(InvalidToken, match="identificador"):
            RefreshTokenUseCase(user_repository, token_manager).execute(
                RefreshTokenCommand(refresh_token="refresh-token")
            )

        user_repository.get_by_id.assert_not_called()

    def test_missing_user_raises_invalid_token(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(subject="99", jti="jti")
        user_repository.get_by_id.return_value = None

        with pytest.raises(InvalidToken, match="Usuario del token no encontrado"):
            RefreshTokenUseCase(user_repository, token_manager).execute(
                RefreshTokenCommand(refresh_token="refresh-token")
            )

        token_manager.create_access_token.assert_not_called()

    def test_invalid_subject_raises_invalid_token(self):
        user_repository = MagicMock(spec=IUserRepository)
        token_manager = MagicMock(spec=ITokenManager)
        token_manager.decode_refresh_token.return_value = _token_payload(
            subject="not-an-int", jti="jti"
        )

        with pytest.raises(InvalidToken, match="sujeto inválido"):
            RefreshTokenUseCase(user_repository, token_manager).execute(
                RefreshTokenCommand(refresh_token="refresh-token")
            )

        user_repository.get_by_id.assert_not_called()
        token_manager.create_access_token.assert_not_called()


def _token_payload(subject: str, version: int = 0, jti: str | None = "jti-1") -> TokenPayload:
    return TokenPayload(
        session_id="session-id",
        subject=subject,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        token_version=version,
        jti=jti,
    )
