"""
Integration tests — dependencias de autenticación/autorización en rutas protegidas.

Usa JWT real con clave controlada y mantiene los use cases de bookings mockeados.
"""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from domain.auth.user_entity import Role
from infrastructure.security.jwt_token_manager import JwtTokenManager

pytestmark = pytest.mark.integration

_SECRET = "test-secret-12345678901234567890"  # Mínimo recomendado de 32 caracteres para SHA256


@pytest.fixture
def protected_api_client() -> Iterator[TestClient]:
    from api.dependencies import get_booking_use_cases, get_token_manager, get_user_repository
    from main import app
    from tests.helpers import make_user

    mock_use_cases = MagicMock()
    mock_use_cases.list_query.execute.return_value = []
    app.dependency_overrides[get_booking_use_cases] = lambda: mock_use_cases
    app.dependency_overrides[get_token_manager] = lambda: JwtTokenManager(secret_key=_SECRET)

    mock_user_repository = MagicMock()
    mock_user_repository.get_by_id.return_value = make_user(id=1, role=Role.LIMPIADORA)
    app.dependency_overrides[get_user_repository] = lambda: mock_user_repository

    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_booking_use_cases, None)
        app.dependency_overrides.pop(get_token_manager, None)
        app.dependency_overrides.pop(get_user_repository, None)


def _bearer_token(role: Role) -> str:
    token = JwtTokenManager(secret_key=_SECRET).create_access_token(
        subject="1",
        claims={"username": "user", "role": role},
    )
    return f"Bearer {token}"


class TestProtectedBookings:
    def test_bookings_without_token_returns_401(self, protected_api_client):
        response = protected_api_client.get("/api/v1/bookings/")

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"

    def test_bookings_with_non_admin_token_returns_403(self, protected_api_client):
        response = protected_api_client.get(
            "/api/v1/bookings/",
            headers={"Authorization": _bearer_token(Role.LIMPIADORA)},
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "Permiso denegado. El usuario no es administrador."}

    def test_bookings_with_malformed_token_returns_401(self, protected_api_client):
        response = protected_api_client.get(
            "/api/v1/bookings/",
            headers={"Authorization": "Bearer not-a-token"},
        )

        assert response.status_code == 401
        assert response.headers["WWW-Authenticate"] == "Bearer"
