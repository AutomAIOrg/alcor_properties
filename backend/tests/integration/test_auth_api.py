"""
Integration tests — endpoint HTTP de autenticación.

FastAPI TestClient con el caso de uso de login inyectado como MagicMock.
"""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from application.auth.login_use_case import LoginCredentials, LoginResult
from application.auth.refresh_token_use_case import RefreshTokenCommand, RefreshTokenResult
from domain.exceptions import InvalidCredentials, InvalidToken

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_login_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_refresh_token_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_forgot_password_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def auth_api_client(
    mock_login_use_case: MagicMock,
    mock_refresh_token_use_case: MagicMock,
    mock_forgot_password_use_case: MagicMock,
) -> Iterator[TestClient]:
    from api.dependencies import (
        get_forgot_password_use_case,
        get_login_use_case,
        get_refresh_token_use_case,
    )
    from main import app

    app.dependency_overrides[get_login_use_case] = lambda: mock_login_use_case
    app.dependency_overrides[get_refresh_token_use_case] = lambda: mock_refresh_token_use_case
    app.dependency_overrides[get_forgot_password_use_case] = lambda: mock_forgot_password_use_case

    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_login_use_case, None)
        app.dependency_overrides.pop(get_refresh_token_use_case, None)
        app.dependency_overrides.pop(get_forgot_password_use_case, None)


class TestLoginEndpoint:
    def test_login_returns_bearer_token_for_valid_credentials(
        self,
        auth_api_client,
        mock_login_use_case,
    ):
        mock_login_use_case.execute.return_value = LoginResult(
            access_token="jwt-token",
            refresh_token="refresh-token",
        )

        response = auth_api_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-password"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "access_token": "jwt-token",
            "refresh_token": "refresh-token",
            "token_type": "bearer",
        }
        mock_login_use_case.execute.assert_called_once_with(
            LoginCredentials(username="admin", password="admin-password")
        )

    def test_login_returns_401_for_invalid_credentials(
        self,
        auth_api_client,
        mock_login_use_case,
    ):
        mock_login_use_case.execute.side_effect = InvalidCredentials()

        response = auth_api_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "wrong-password"},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Usuario o contraseña inválidos"}

    def test_login_invalid_payload_returns_422(self, auth_api_client):
        response = auth_api_client.post("/api/v1/auth/login", json={"username": "admin"})

        assert response.status_code == 422


class TestRefreshEndpoint:
    def test_refresh_returns_new_access_token(
        self,
        auth_api_client,
        mock_refresh_token_use_case,
    ):
        mock_refresh_token_use_case.execute.return_value = RefreshTokenResult(
            access_token="new-access-token"
        )

        response = auth_api_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "refresh-token"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "access_token": "new-access-token",
            "token_type": "bearer",
        }
        mock_refresh_token_use_case.execute.assert_called_once_with(
            RefreshTokenCommand(refresh_token="refresh-token")
        )

    def test_refresh_returns_401_for_invalid_token(
        self,
        auth_api_client,
        mock_refresh_token_use_case,
    ):
        mock_refresh_token_use_case.execute.side_effect = InvalidToken()

        response = auth_api_client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid-token"},
        )

        assert response.status_code == 401

    def test_refresh_invalid_payload_returns_422(self, auth_api_client):
        response = auth_api_client.post("/api/v1/auth/refresh", json={})

        assert response.status_code == 422


class TestForgotPasswordEndpoint:
    def test_forgot_password_returns_uniform_message_and_normalizes_email(
        self,
        auth_api_client,
        mock_forgot_password_use_case,
    ):
        response = auth_api_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "  Admin@Example.COM  "},
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": (
                "Si el email está registrado, recibirás un enlace para restablecer tu contraseña."
            )
        }
        mock_forgot_password_use_case.execute.assert_called_once_with("admin@example.com")

    def test_forgot_password_invalid_email_returns_422(
        self,
        auth_api_client,
        mock_forgot_password_use_case,
    ):
        response = auth_api_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "not-an-email"},
        )

        assert response.status_code == 422
        mock_forgot_password_use_case.execute.assert_not_called()
