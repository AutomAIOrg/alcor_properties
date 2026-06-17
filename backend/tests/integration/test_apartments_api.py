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

        apartment_api_client.get("/api/v1/apartments/search?min_rooms=2&min_occupants=4")

        filters = mock_search_apartments_use_case.execute.call_args[0][0]
        assert filters.min_rooms == 2
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
# GET /api/v1/apartments/stats/{apartment_id}
# ---------------------------------------------------------------------------


class TestGetApartmentStats:
    def test_returns_200_and_forwards_full_date_range(
        self, apartment_api_client, mock_get_apartment_stats_use_case
    ):
        from datetime import date

        mock_get_apartment_stats_use_case.execute.return_value = {
            "apartment_id": "R180",
            "apartment": make_apartment(apartment_id="R180").model_dump(),
            "filtered_range": {
                "start_date": date(2026, 6, 1),
                "end_date": date(2026, 6, 30),
                "total_bookings": 0,
                "active_bookings": 0,
                "cancelled_bookings": 0,
                "cancellation_rate": None,
                "total_nights": 0,
                "avg_nights_per_booking": None,
                "total_persons": 0,
                "avg_persons_per_booking": None,
                "total_revenue": None,
                "avg_revenue_per_booking": None,
                "avg_revenue_per_night": None,
                "total_charges": None,
                "total_electric_allowance": None,
                "occupancy_pct": None,
                "status_breakdown": {},
            },
            "by_year": [],
        }

        response = apartment_api_client.get(
            "/api/v1/apartments/stats/R180?start_date=2026-06-01&end_date=2026-06-30"
        )

        assert response.status_code == 200
        mock_get_apartment_stats_use_case.execute.assert_called_once_with(
            "R180",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
        )
        assert response.json()["apartment_id"] == "R180"

    def test_returns_422_when_only_start_date_provided(
        self, apartment_api_client, mock_get_apartment_stats_use_case
    ):
        response = apartment_api_client.get("/api/v1/apartments/stats/R180?start_date=2026-06-01")

        assert response.status_code == 422
        assert "start_date y end_date deben informarse juntas" in response.text
        mock_get_apartment_stats_use_case.execute.assert_not_called()

    def test_returns_422_when_only_end_date_provided(
        self, apartment_api_client, mock_get_apartment_stats_use_case
    ):
        response = apartment_api_client.get("/api/v1/apartments/stats/R180?end_date=2026-06-30")

        assert response.status_code == 422
        assert "start_date y end_date deben informarse juntas" in response.text
        mock_get_apartment_stats_use_case.execute.assert_not_called()
