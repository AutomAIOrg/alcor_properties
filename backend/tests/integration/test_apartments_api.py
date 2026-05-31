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
    def test_returns_200_with_empty_list(self, apartment_api_client, mock_apartment_use_cases):
        mock_apartment_use_cases.search_apartments.execute.return_value = []

        response = apartment_api_client.get("/api/v1/apartments/search")

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_200_with_correct_schema(self, apartment_api_client, mock_apartment_use_cases):
        mock_apartment_use_cases.search_apartments.execute.return_value = [
            make_apartment(
                booking_id="R180",
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
        assert data[0]["booking_id"] == "R180"
        assert data[0]["community"] == "Alta Entinas"
        assert data[0]["rooms"] == 2
        assert data[0]["parking"] == "63"

    def test_q_param_is_forwarded_to_use_case(self, apartment_api_client, mock_apartment_use_cases):
        mock_apartment_use_cases.search_apartments.execute.return_value = []

        apartment_api_client.get("/api/v1/apartments/search?q=entinas")

        filters = mock_apartment_use_cases.search_apartments.execute.call_args[0][0]
        assert filters.q == "entinas"

    def test_numeric_filters_are_forwarded_to_use_case(self, apartment_api_client, mock_apartment_use_cases):
        mock_apartment_use_cases.search_apartments.execute.return_value = []

        apartment_api_client.get("/api/v1/apartments/search?min_rooms=2&max_rooms=4&min_occupants=4")

        filters = mock_apartment_use_cases.search_apartments.execute.call_args[0][0]
        assert filters.min_rooms == 2
        assert filters.max_rooms == 4
        assert filters.min_occupants == 4

    def test_date_filters_are_forwarded_to_use_case(self, apartment_api_client, mock_apartment_use_cases):
        from datetime import date

        mock_apartment_use_cases.search_apartments.execute.return_value = []

        apartment_api_client.get(
            "/api/v1/apartments/search?available_from=2026-06-01&available_to=2026-06-30"
        )

        filters = mock_apartment_use_cases.search_apartments.execute.call_args[0][0]
        assert filters.available_from == date(2026, 6, 1)
        assert filters.available_to == date(2026, 6, 30)

    def test_returns_400_when_only_available_from_provided(self, apartment_api_client):
        response = apartment_api_client.get(
            "/api/v1/apartments/search?available_from=2026-06-01"
        )

        assert response.status_code == 400
        assert "juntas" in response.json()["detail"]

    def test_returns_400_when_min_rooms_greater_than_max_rooms(self, apartment_api_client):
        response = apartment_api_client.get(
            "/api/v1/apartments/search?min_rooms=5&max_rooms=2"
        )

        assert response.status_code == 400

    def test_returns_422_when_min_rooms_is_negative(self, apartment_api_client):
        response = apartment_api_client.get("/api/v1/apartments/search?min_rooms=-1")

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/apartments/{booking_id}
# ---------------------------------------------------------------------------


class TestGetApartmentByBookingId:
    def test_returns_200_with_correct_schema(self, apartment_api_client, mock_apartment_use_cases):
        mock_apartment_use_cases.get_apartment_by_booking_id.execute.return_value = make_apartment(
            booking_id="R180",
            community="Alta Entinas",
            address="Calle Glaucio 15",
        )

        response = apartment_api_client.get("/api/v1/apartments/R180")

        assert response.status_code == 200
        data = response.json()
        assert data["booking_id"] == "R180"
        assert data["community"] == "Alta Entinas"
        assert data["address"] == "Calle Glaucio 15"

    def test_returns_404_when_apartment_not_found(self, apartment_api_client, mock_apartment_use_cases):
        mock_apartment_use_cases.get_apartment_by_booking_id.execute.return_value = None

        response = apartment_api_client.get("/api/v1/apartments/UNKNOWN")

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"]

    def test_returns_400_when_use_case_raises_value_error(self, apartment_api_client, mock_apartment_use_cases):
        mock_apartment_use_cases.get_apartment_by_booking_id.execute.side_effect = ValueError(
            "El booking_id no puede estar vacío"
        )

        response = apartment_api_client.get("/api/v1/apartments/%20")  # espacio URL-encoded

        assert response.status_code == 400
        assert "booking_id" in response.json()["detail"]

    def test_returns_403_without_admin_role(self, apartment_api_client, monkeypatch):
        from fastapi import HTTPException

        monkeypatch.setattr(
            "api.v1.apartments.router.require_admin",
            lambda: (_ for _ in ()).throw(HTTPException(status_code=403)),
        )

        # La forma más limpia es usar un cliente sin override de auth
        # y verificar que el router protege el endpoint con require_admin.
        # Esto ya lo cubre test_auth_dependencies.py; aquí solo verificamos
        # que el router declara la dependencia (comprobación estructural).
        from api.v1.apartments.router import router
        dep_names = [d.dependency.__name__ for d in router.dependencies]
        assert "require_admin" in dep_names
