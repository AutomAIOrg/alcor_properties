"""
Integration tests — endpoints HTTP de gestión de contraseñas.

Cubre el cambio de contraseña del usuario autenticado (auth) y el
restablecimiento a la contraseña inicial por parte de un administrador (users).
FastAPI TestClient con los casos de uso y el usuario actual inyectados como mocks.
"""

from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from application.auth.change_initial_password_use_case import (
    ChangeInitialPasswordCommand,
    ChangeInitialPasswordResult,
)
from application.auth.change_password_use_case import ChangePasswordCommand
from application.users.reset_user_password_use_case import ResetUserPasswordCommand
from config import settings
from domain.auth.user_entity import Role
from domain.exceptions import DomainValidationError, UserNotFound
from tests.helpers import make_user

pytestmark = pytest.mark.integration


@pytest.fixture
def mock_change_password_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_reset_user_password_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_change_initial_password_use_case() -> MagicMock:
    return MagicMock()


@pytest.fixture
def password_api_client(
    mock_change_password_use_case: MagicMock,
    mock_reset_user_password_use_case: MagicMock,
    mock_change_initial_password_use_case: MagicMock,
) -> Iterator[TestClient]:
    from api.dependencies import (
        get_change_initial_password_use_case,
        get_change_password_use_case,
        get_current_user,
        get_reset_user_password_use_case,
    )
    from main import app

    admin_user = make_user(id=7, role=Role.ADMIN)

    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[get_change_password_use_case] = lambda: mock_change_password_use_case
    app.dependency_overrides[get_reset_user_password_use_case] = lambda: (
        mock_reset_user_password_use_case
    )
    app.dependency_overrides[get_change_initial_password_use_case] = lambda: (
        mock_change_initial_password_use_case
    )

    try:
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_change_password_use_case, None)
        app.dependency_overrides.pop(get_reset_user_password_use_case, None)
        app.dependency_overrides.pop(get_change_initial_password_use_case, None)


class TestChangePasswordEndpoint:
    def test_change_password_forwards_current_user_id(
        self, password_api_client, mock_change_password_use_case
    ):
        response = password_api_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "actual123", "new_password": "nueva123"},
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Contraseña actualizada correctamente."}
        mock_change_password_use_case.execute.assert_called_once_with(
            ChangePasswordCommand(user_id=7, current_password="actual123", new_password="nueva123")
        )

    def test_change_password_returns_422_on_validation_error(
        self, password_api_client, mock_change_password_use_case
    ):
        mock_change_password_use_case.execute.side_effect = DomainValidationError(
            "La contraseña actual no es correcta"
        )

        response = password_api_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "incorrecta", "new_password": "nueva123"},
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "La contraseña actual no es correcta"}

    def test_change_password_invalid_payload_returns_422(self, password_api_client):
        response = password_api_client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "actual123"},
        )

        assert response.status_code == 422


class TestChangeInitialPasswordEndpoint:
    def test_change_initial_password_returns_fresh_tokens(
        self, password_api_client, mock_change_initial_password_use_case
    ):
        mock_change_initial_password_use_case.execute.return_value = ChangeInitialPasswordResult(
            access_token="new-access-token",
            refresh_token="new-refresh-token",
        )

        response = password_api_client.post(
            "/api/v1/auth/change-initial-password",
            json={"new_password": "nueva123"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "access_token": "new-access-token",
            "refresh_token": "new-refresh-token",
            "token_type": "bearer",
        }
        mock_change_initial_password_use_case.execute.assert_called_once_with(
            ChangeInitialPasswordCommand(user_id=7, new_password="nueva123")
        )

    def test_change_initial_password_returns_422_on_validation_error(
        self, password_api_client, mock_change_initial_password_use_case
    ):
        mock_change_initial_password_use_case.execute.side_effect = DomainValidationError(
            "El usuario ya tiene una contraseña propia"
        )

        response = password_api_client.post(
            "/api/v1/auth/change-initial-password",
            json={"new_password": "nueva123"},
        )

        assert response.status_code == 422
        assert response.json() == {"detail": "El usuario ya tiene una contraseña propia"}

    def test_change_initial_password_invalid_payload_returns_422(self, password_api_client):
        response = password_api_client.post("/api/v1/auth/change-initial-password", json={})

        assert response.status_code == 422


class TestResetUserPasswordEndpoint:
    def test_reset_password_forwards_initial_password(
        self, password_api_client, mock_reset_user_password_use_case
    ):
        response = password_api_client.post("/api/v1/users/3/reset-password")

        assert response.status_code == 200
        assert response.json() == {"message": "Contraseña restablecida a la contraseña inicial."}
        mock_reset_user_password_use_case.execute.assert_called_once_with(
            ResetUserPasswordCommand(user_id=3, initial_password=settings.DEFAULT_PASSWORD)
        )

    def test_reset_password_returns_404_for_unknown_user(
        self, password_api_client, mock_reset_user_password_use_case
    ):
        mock_reset_user_password_use_case.execute.side_effect = UserNotFound()

        response = password_api_client.post("/api/v1/users/404/reset-password")

        assert response.status_code == 404
