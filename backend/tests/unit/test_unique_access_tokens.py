from datetime import UTC, datetime
from unittest.mock import patch

from infrastructure.security.jwt_token_manager import JwtTokenManager


def test_access_tokens_are_unique_with_same_timestamp():
    manager = JwtTokenManager(secret_key="test-key" * 8)
    with patch("infrastructure.security.jwt_token_manager.datetime") as clock:
        clock.now.return_value = datetime(2026, 10, 11, tzinfo=UTC)
        assert manager.create_access_token("1") != manager.create_access_token("1")
