"""
Integration tests — endpoints HTTP de settings.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from api.dependencies import get_current_user
from domain.auth.user_entity import Role
from domain.exceptions import DomainValidationError
from main import app
from tests.helpers import make_user

pytestmark = pytest.mark.integration


class TestGetCleaningRate:
    def test_returns_current_rate(self, settings_api_client, mock_get_cleaning_rate_use_case):
        mock_get_cleaning_rate_use_case.execute.return_value = Decimal("15.00")

        response = settings_api_client.get("/api/v1/settings/cleaning-rate")

        assert response.status_code == 200
        assert response.json() == {"cleaning_hourly_rate": 15.0}

    def test_limpiadora_can_read_rate(self, settings_api_client, mock_get_cleaning_rate_use_case):
        mock_get_cleaning_rate_use_case.execute.return_value = Decimal("12.00")

        response = settings_api_client.get("/api/v1/settings/cleaning-rate")

        assert response.status_code == 200


class TestUpdateCleaningRate:
    def test_admin_can_update_rate(self, settings_api_client, mock_update_cleaning_rate_use_case):
        admin_user = make_user(role=Role.ADMIN)
        app.dependency_overrides[get_current_user] = lambda: admin_user
        mock_update_cleaning_rate_use_case.execute.return_value = Decimal("18.50")

        try:
            response = settings_api_client.put(
                "/api/v1/settings/cleaning-rate",
                json={"cleaning_hourly_rate": "18.50"},
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200
        assert response.json() == {"cleaning_hourly_rate": 18.5}

    def test_limpiadora_cannot_update_rate(
        self, settings_api_client, mock_update_cleaning_rate_use_case
    ):
        response = settings_api_client.put(
            "/api/v1/settings/cleaning-rate",
            json={"cleaning_hourly_rate": "20.00"},
        )

        assert response.status_code == 403
        mock_update_cleaning_rate_use_case.execute.assert_not_called()

    def test_negative_rate_returns_422(
        self, settings_api_client, mock_update_cleaning_rate_use_case
    ):
        admin_user = make_user(role=Role.ADMIN)
        app.dependency_overrides[get_current_user] = lambda: admin_user
        mock_update_cleaning_rate_use_case.execute.side_effect = DomainValidationError(
            "El precio por hora de limpieza no puede ser negativo."
        )

        try:
            response = settings_api_client.put(
                "/api/v1/settings/cleaning-rate",
                json={"cleaning_hourly_rate": "-1"},
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 422


class TestSettingsPermissions:
    def test_unauthenticated_get_returns_401(self):
        from api.dependencies import get_cleaning_rate_use_case, get_update_cleaning_rate_use_case

        deps = (
            get_cleaning_rate_use_case,
            get_update_cleaning_rate_use_case,
            get_current_user,
        )
        saved_overrides = dict(app.dependency_overrides)
        try:
            for dep in deps:
                app.dependency_overrides.pop(dep, None)

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.get("/api/v1/settings/cleaning-rate")
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(saved_overrides)

        assert response.status_code == 401

    def test_non_cleaning_role_get_returns_403(
        self, settings_api_client, mock_get_cleaning_rate_use_case
    ):
        unauthorized = MagicMock()
        unauthorized.role = "guest"
        app.dependency_overrides[get_current_user] = lambda: unauthorized
        mock_get_cleaning_rate_use_case.execute.return_value = Decimal("10")

        try:
            response = settings_api_client.get("/api/v1/settings/cleaning-rate")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 403
