"""
Integration tests — endpoints HTTP de apartments.

FastAPI TestClient con use cases inyectados como MagicMock.
Sin base de datos real: la dependencia get_apartment_use_cases se sobreescribe.
"""

import pytest

from tests.helpers import make_apartment

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# GET /api/v1/apartments/search
# ---------------------------------------------------------------------------


class TestSearchApartments:
    def test_returns_200_with_empty_list(
        self, apartment_api_client, mock_search_apartments_use_case
    ):
        mock_search_apartments_use_case.execute.return_value = []

        response = apartment_api_client.get("/api/v1/apartments/search")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_200_with_correct_schema(
        self, apartment_api_client, mock_search_apartments_use_case
    ):
        mock_search_apartments_use_case.execute.return_value = [
            make_apartment(
                apartment_id="R180",
                community="Alta Entinas",
                rooms=2,
                bathrooms=2,
                parking="63",
                total_occupants=6,
            )
        ]

        response = apartment_api_client.get("/api/v1/apartments/search")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["apartment_id"] == "R180"
        assert data[0]["community"] == "Alta Entinas"
        assert data[0]["rooms"] == 2
        assert data[0]["parking"] == "63"

    def test_q_param_is_forwarded_to_use_case(
        self, apartment_api_client, mock_search_apartments_use_case
    ):
        mock_search_apartments_use_case.execute.return_value = []

        apartment_api_client.get("/api/v1/apartments/search?q=entinas")

        filters = mock_search_apartments_use_case.execute.call_args[0][0]
        assert filters.q == "entinas"

    def test_numeric_filters_are_forwarded_to_use_case(
        self, apartment_api_client, mock_search_apartments_use_case
    ):
        mock_search_apartments_use_case.execute.return_value = []

        apartment_api_client.get(
            "/api/v1/apartments/search?min_rooms=2&max_rooms=4&min_occupants=4"
        )

        filters = mock_search_apartments_use_case.execute.call_args[0][0]
        assert filters.min_rooms == 2
        assert filters.max_rooms == 4
        assert filters.min_occupants == 4

    def test_date_filters_are_forwarded_to_use_case(
        self, apartment_api_client, mock_search_apartments_use_case
    ):
        from datetime import date

        mock_search_apartments_use_case.execute.return_value = []

        apartment_api_client.get(
            "/api/v1/apartments/search?available_from=2026-06-01&available_to=2026-06-30"
        )

        filters = mock_search_apartments_use_case.execute.call_args[0][0]
        assert filters.available_from == date(2026, 6, 1)
        assert filters.available_to == date(2026, 6, 30)

    def test_returns_422_when_only_available_from_provided(self, apartment_api_client):
        response = apartment_api_client.get("/api/v1/apartments/search?available_from=2026-06-01")

        assert response.status_code == 422
        assert "available_from y available_to deben informarse juntas" in response.text

    def test_returns_422_when_min_rooms_greater_than_max_rooms(
        self,
        apartment_api_client,
    ):
        response = apartment_api_client.get("/api/v1/apartments/search?min_rooms=5&max_rooms=2")

        assert response.status_code == 422
        assert "min_rooms no puede ser mayor que max_rooms" in response.text

    def test_returns_422_when_min_rooms_is_negative(self, apartment_api_client):
        response = apartment_api_client.get("/api/v1/apartments/search?min_rooms=-1")

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/apartments/{apartment_id}
# ---------------------------------------------------------------------------


class TestGetApartmentByApartmentId:
    def test_returns_200_with_correct_schema(
        self, apartment_api_client, mock_get_apartment_by_id_use_case
    ):
        mock_get_apartment_by_id_use_case.execute.return_value = make_apartment(
            apartment_id="R180",
            community="Alta Entinas",
            address="Calle Glaucio 15",
        )

        response = apartment_api_client.get("/api/v1/apartments/R180")

        assert response.status_code == 200
        data = response.json()
        assert data["apartment_id"] == "R180"
        assert data["community"] == "Alta Entinas"
        assert data["address"] == "Calle Glaucio 15"

    def test_returns_404_when_apartment_not_found(
        self, apartment_api_client, mock_get_apartment_by_id_use_case
    ):
        mock_get_apartment_by_id_use_case.execute.return_value = None

        response = apartment_api_client.get("/api/v1/apartments/UNKNOWN")

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_returns_400_when_use_case_raises_value_error(
        self, apartment_api_client, mock_get_apartment_by_id_use_case
    ):
        mock_get_apartment_by_id_use_case.execute.side_effect = ValueError(
            "El apartment_id no puede estar vacío"
        )

        response = apartment_api_client.get("/api/v1/apartments/%20")  # espacio URL-encoded

        assert response.status_code == 400
        assert "apartment_id" in response.json()["detail"]

    def test_returns_403_when_user_is_not_admin(self, apartment_api_client):
        from datetime import UTC, datetime, timedelta

        from api.dependencies import get_current_user
        from domain.auth.token_payload_entity import TokenPayload
        from domain.auth.user_entity import Role
        from main import app

        now = datetime.now(UTC)
        cleaner_payload = TokenPayload(
            subject="2",
            expires_at=now + timedelta(minutes=30),
            issued_at=now,
            username="cleaner",
            role=Role.LIMPIADORA,
        )
        app.dependency_overrides[get_current_user] = lambda: cleaner_payload

        response = apartment_api_client.get("/api/v1/apartments/search")

        assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /api/v1/apartments/all
# ---------------------------------------------------------------------------


class TestGetAllApartments:
    def test_returns_200_with_correct_schema(
        self, apartment_api_client, mock_get_all_apartments_use_case
    ):
        mock_get_all_apartments_use_case.execute.return_value = [
            make_apartment(
                apartment_id="R180",
                community="Alta Entinas",
                apartment_description="Apartamento familiar",
                address="Calle Glaucio 15",
                rooms=2,
                bathrooms=2,
                parking="63",
                total_occupants=6,
                owner_name="Katarzyna Tokarska",
                email="owner@example.com",
                phone="+34 600 000 000",
            )
        ]

        response = apartment_api_client.get("/api/v1/apartments/all")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0] == {
            "apartment_id": "R180",
            "community": "Alta Entinas",
            "apartment_description": "Apartamento familiar",
            "address": "Calle Glaucio 15",
            "rooms": 2,
            "bathrooms": 2,
            "parking": "63",
            "total_occupants": 6,
            "owner_name": "Katarzyna Tokarska",
            "email": "owner@example.com",
            "phone": "+34 600 000 000",
        }


# ---------------------------------------------------------------------------
# POST /api/v1/apartments/
# ---------------------------------------------------------------------------


class TestCreateApartment:
    _VALID_PAYLOAD = {
        "apartment_id": "R184",
        "community": "Residencial Norte",
        "apartment_description": "Apartamento R184",
        "address": "Calle Mayor 1",
        "rooms": 2,
        "bathrooms": 1,
        "parking": "P-12",
        "total_occupants": 4,
        "owner_name": "Juan Pérez",
        "email": "juan@example.com",
        "phone": "+34600000000",
    }

    def test_valid_payload_returns_success_message(
        self, apartment_api_client, mock_create_apartment_use_case
    ):
        from domain.apartments.entity import Apartment

        response = apartment_api_client.post("/api/v1/apartments/", json=self._VALID_PAYLOAD)

        assert response.status_code == 200
        assert response.json() == {"message": "Apartamento creado correctamente"}

        called_apartment = mock_create_apartment_use_case.execute.call_args[0][0]
        assert isinstance(called_apartment, Apartment)
        assert called_apartment.apartment_id == "R184"
        assert called_apartment.community == "Residencial Norte"
        assert called_apartment.rooms == 2
        assert called_apartment.total_occupants == 4

    def test_returns_409_when_apartment_already_exists(
        self, apartment_api_client, mock_create_apartment_use_case
    ):
        from domain.exceptions import ApartmentAlreadyExistsError

        mock_create_apartment_use_case.execute.side_effect = ApartmentAlreadyExistsError("R184")

        response = apartment_api_client.post("/api/v1/apartments/", json=self._VALID_PAYLOAD)

        assert response.status_code == 409
        assert "R184" in response.json()["detail"]

    def test_returns_422_when_rooms_is_negative(self, apartment_api_client):
        payload = {**self._VALID_PAYLOAD, "rooms": -1}

        response = apartment_api_client.post("/api/v1/apartments/", json=payload)

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/v1/apartments/{apartment_id}
# ---------------------------------------------------------------------------


class TestUpdateApartment:
    _VALID_PAYLOAD = {
        "community": "Residencial Sur",
        "apartment_description": "Apartamento actualizado",
        "address": "Calle Nueva 5",
        "rooms": 3,
        "bathrooms": 2,
        "parking": "P-22",
        "total_occupants": 6,
        "owner_name": "María López",
        "email": "maria@example.com",
        "phone": "600111222",
    }

    def test_valid_update_returns_success_message(
        self, apartment_api_client, mock_update_apartment_use_case
    ):
        from domain.apartments.entity import Apartment

        response = apartment_api_client.put("/api/v1/apartments/R180", json=self._VALID_PAYLOAD)

        assert response.status_code == 200
        assert response.json() == {"message": "Apartamento actualizado correctamente"}

        called_apartment = mock_update_apartment_use_case.execute.call_args[0][0]
        assert isinstance(called_apartment, Apartment)
        assert called_apartment.apartment_id == "R180"
        assert called_apartment.community == "Residencial Sur"
        assert called_apartment.rooms == 3
        assert "apartment_id" not in self._VALID_PAYLOAD

    def test_returns_404_when_apartment_not_found(
        self, apartment_api_client, mock_update_apartment_use_case
    ):
        from domain.exceptions import ApartmentNotFoundError

        mock_update_apartment_use_case.execute.side_effect = ApartmentNotFoundError("R180")

        response = apartment_api_client.put("/api/v1/apartments/R180", json=self._VALID_PAYLOAD)

        assert response.status_code == 404
        assert "R180" in response.json()["detail"]


# ---------------------------------------------------------------------------
# DELETE /api/v1/apartments/{apartment_id}
# ---------------------------------------------------------------------------


class TestDeleteApartment:
    def test_deletes_and_returns_success_message(
        self, apartment_api_client, mock_delete_apartment_use_case
    ):
        response = apartment_api_client.delete("/api/v1/apartments/R180")

        assert response.status_code == 200
        assert response.json() == {"message": "Apartamento eliminado correctamente"}
        mock_delete_apartment_use_case.execute.assert_called_once_with("R180")

    def test_returns_404_when_apartment_not_found(
        self, apartment_api_client, mock_delete_apartment_use_case
    ):
        from domain.exceptions import ApartmentNotFoundError

        mock_delete_apartment_use_case.execute.side_effect = ApartmentNotFoundError("R180")

        response = apartment_api_client.delete("/api/v1/apartments/R180")

        assert response.status_code == 404
        assert "R180" in response.json()["detail"]

    def test_returns_409_when_apartment_has_bookings(
        self, apartment_api_client, mock_delete_apartment_use_case
    ):
        from domain.exceptions import ApartmentHasBookingsError

        mock_delete_apartment_use_case.execute.side_effect = ApartmentHasBookingsError("R180")

        response = apartment_api_client.delete("/api/v1/apartments/R180")

        assert response.status_code == 409
        assert "reservas" in response.json()["detail"].lower()
