"""
Integration tests — endpoints HTTP de cleaning-types.

FastAPI TestClient con casos de uso inyectados como MagicMock.
"""

from decimal import Decimal

import pytest

from api.dependencies import get_current_user
from domain.auth.user_entity import Role
from domain.exceptions import CleaningTypeAlreadyExistsError, CleaningTypeNotFoundError
from main import app
from tests.helpers import make_cleaning_type, make_user

pytestmark = pytest.mark.integration

_VALID_PAYLOAD = {"name": "Limpieza fin de semana", "hourly_rate": "20.00", "active": True}


class TestListCleaningTypes:
    def test_returns_200_with_types(
        self, cleaning_types_api_client, mock_list_cleaning_types_use_case
    ):
        mock_list_cleaning_types_use_case.execute.return_value = [
            make_cleaning_type(cleaning_type_id=1, name="Normal", hourly_rate=Decimal("15.00"))
        ]

        response = cleaning_types_api_client.get("/api/v1/cleaning-types/")

        assert response.status_code == 200
        body = response.json()
        assert body[0]["name"] == "Normal"
        assert body[0]["hourly_rate"] == 15.0

    def test_active_only_query_is_forwarded(
        self, cleaning_types_api_client, mock_list_cleaning_types_use_case
    ):
        mock_list_cleaning_types_use_case.execute.return_value = []

        cleaning_types_api_client.get("/api/v1/cleaning-types/?active_only=true")

        mock_list_cleaning_types_use_case.execute.assert_called_once_with(active_only=True)

    def test_cleaner_can_list(self, cleaning_types_api_client, mock_list_cleaning_types_use_case):
        app.dependency_overrides[get_current_user] = lambda: make_user(
            id=2, username="limpiadora", role=Role.LIMPIADORA
        )
        mock_list_cleaning_types_use_case.execute.return_value = []
        try:
            response = cleaning_types_api_client.get("/api/v1/cleaning-types/")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200


class TestCreateCleaningType:
    def test_admin_creates_returns_201(
        self, cleaning_types_api_client, mock_create_cleaning_type_use_case
    ):
        mock_create_cleaning_type_use_case.execute.return_value = make_cleaning_type(
            cleaning_type_id=9, name="Limpieza fin de semana", hourly_rate=Decimal("20.00")
        )

        response = cleaning_types_api_client.post("/api/v1/cleaning-types/", json=_VALID_PAYLOAD)

        assert response.status_code == 201
        assert response.json()["cleaning_type_id"] == 9

    def test_cleaner_cannot_create_returns_403(self, cleaning_types_api_client):
        app.dependency_overrides[get_current_user] = lambda: make_user(
            id=2, username="limpiadora", role=Role.LIMPIADORA
        )
        try:
            response = cleaning_types_api_client.post(
                "/api/v1/cleaning-types/", json=_VALID_PAYLOAD
            )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 403

    def test_duplicate_name_returns_409(
        self, cleaning_types_api_client, mock_create_cleaning_type_use_case
    ):
        mock_create_cleaning_type_use_case.execute.side_effect = CleaningTypeAlreadyExistsError(
            "Limpieza fin de semana"
        )

        response = cleaning_types_api_client.post("/api/v1/cleaning-types/", json=_VALID_PAYLOAD)

        assert response.status_code == 409


class TestUpdateCleaningType:
    def test_admin_updates_returns_200(
        self, cleaning_types_api_client, mock_update_cleaning_type_use_case
    ):
        mock_update_cleaning_type_use_case.execute.return_value = make_cleaning_type(
            cleaning_type_id=3, name="Renombrada", hourly_rate=Decimal("18.00"), active=False
        )

        response = cleaning_types_api_client.put(
            "/api/v1/cleaning-types/3",
            json={"name": "Renombrada", "hourly_rate": "18.00", "active": False},
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Renombrada"
        assert response.json()["active"] is False

    def test_missing_returns_404(
        self, cleaning_types_api_client, mock_update_cleaning_type_use_case
    ):
        mock_update_cleaning_type_use_case.execute.side_effect = CleaningTypeNotFoundError(99)

        response = cleaning_types_api_client.put(
            "/api/v1/cleaning-types/99",
            json={"name": "X", "hourly_rate": "1.00", "active": True},
        )

        assert response.status_code == 404


class TestDeleteCleaningType:
    def test_admin_deletes_returns_204(
        self, cleaning_types_api_client, mock_delete_cleaning_type_use_case
    ):
        response = cleaning_types_api_client.delete("/api/v1/cleaning-types/5")

        assert response.status_code == 204
        mock_delete_cleaning_type_use_case.execute.assert_called_once_with(5)

    def test_missing_returns_404(
        self, cleaning_types_api_client, mock_delete_cleaning_type_use_case
    ):
        mock_delete_cleaning_type_use_case.execute.side_effect = CleaningTypeNotFoundError(5)

        response = cleaning_types_api_client.delete("/api/v1/cleaning-types/5")

        assert response.status_code == 404
