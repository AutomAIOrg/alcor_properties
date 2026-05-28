"""
Unit tests — manager JWT.

Se usa una clave fija para que los tokens sean deterministas desde el punto de vista de la
configuración, sin depender del entorno local.
"""

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from domain.auth.user_entity import Role
from domain.exceptions import InvalidToken, TokenExpired
from infrastructure.security.jwt_token_manager import JwtTokenManager

pytestmark = pytest.mark.unit

_SECRET = "test-secret-12345678901234567890"  # Mínimo recomendado de 32 caracteres para SHA256
_ALGORITHM = "HS256"


class TestJwtTokenManager:
    def test_create_and_decode_access_token_round_trip(self):
        manager = JwtTokenManager(
            secret_key=_SECRET,
            algorithm=_ALGORITHM,
            access_token_expire_minutes=15,
        )

        token = manager.create_access_token(
            subject="1",
            claims={"username": "admin", "role": Role.ADMIN},
        )

        payload = manager.decode_access_token(token)
        assert payload.subject == "1"
        assert payload.username == "admin"
        assert payload.role == Role.ADMIN
        assert payload.issued_at is not None
        assert payload.expires_at > payload.issued_at

    def test_create_and_decode_refresh_token_round_trip(self):
        manager = JwtTokenManager(
            secret_key=_SECRET,
            algorithm=_ALGORITHM,
            refresh_token_expire_days=7,
        )

        token = manager.create_refresh_token(subject="1")

        payload = manager.decode_refresh_token(token)
        assert payload.subject == "1"
        assert payload.username is None
        assert payload.role is None
        assert payload.issued_at is not None
        assert payload.expires_at > payload.issued_at

    def test_decode_expired_token_raises_token_expired(self):
        manager = JwtTokenManager(
            secret_key=_SECRET,
            algorithm=_ALGORITHM,
            access_token_expire_minutes=-1,
        )
        token = manager.create_access_token(subject="1", claims={"role": Role.ADMIN})

        with pytest.raises(TokenExpired):
            manager.decode_access_token(token)

    def test_decode_expired_refresh_token_raises_token_expired(self):
        manager = JwtTokenManager(
            secret_key=_SECRET,
            algorithm=_ALGORITHM,
            refresh_token_expire_days=-1,
        )
        token = manager.create_refresh_token(subject="1")

        with pytest.raises(TokenExpired):
            manager.decode_refresh_token(token)

    def test_access_token_is_not_accepted_as_refresh_token(self):
        manager = JwtTokenManager(secret_key=_SECRET, algorithm=_ALGORITHM)
        token = manager.create_access_token(subject="1", claims={"role": Role.ADMIN})

        with pytest.raises(InvalidToken, match="tipo inválido"):
            manager.decode_refresh_token(token)

    def test_refresh_token_is_not_accepted_as_access_token(self):
        manager = JwtTokenManager(secret_key=_SECRET, algorithm=_ALGORITHM)
        token = manager.create_refresh_token(subject="1")

        with pytest.raises(InvalidToken, match="tipo inválido"):
            manager.decode_access_token(token)

    def test_decode_token_with_invalid_role_raises_invalid_token(self):
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": "1",
                "type": "access",
                "username": "admin",
                "role": "superadmin",
                "iat": int(now.timestamp()),
                "exp": int((now + timedelta(minutes=15)).timestamp()),
            },
            _SECRET,
            algorithm=_ALGORITHM,
        )

        with pytest.raises(InvalidToken, match="rol inválido"):
            JwtTokenManager(secret_key=_SECRET, algorithm=_ALGORITHM).decode_access_token(token)
