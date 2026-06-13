"""
Integration tests — endpoints HTTP de bookings.

FastAPI TestClient con use cases inyectados como MagicMock.
Sin base de datos real: la dependencia get_booking_use_cases se sobreescribe.
"""

from datetime import date

import pytest
from sqlalchemy.exc import SQLAlchemyError

from domain.exceptions import BookingConflict, BookingNotFound, DomainValidationError
from tests.helpers import make_booking

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Endpoints de infraestructura (raíz y health)
# ---------------------------------------------------------------------------


class TestInfrastructureEndpoints:
    def test_root_returns_app_metadata(self, api_client):
        response = api_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data

    def test_health_returns_healthy_status_when_database_is_available(
        self, api_client, monkeypatch
    ):
        monkeypatch.setattr("main.check_database_connection", lambda: None)

        response = api_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "database": "ok"}

    def test_health_returns_503_when_database_is_unavailable(self, api_client, monkeypatch):
        def raise_database_error() -> None:
            raise SQLAlchemyError("database unavailable")

        monkeypatch.setattr("main.check_database_connection", raise_database_error)

        response = api_client.get("/health")

        assert response.status_code == 503
        assert response.json() == {"status": "unhealthy", "database": "unavailable"}


# ---------------------------------------------------------------------------
# GET /api/v1/bookings/
# ---------------------------------------------------------------------------


class TestListBookings:
    def test_returns_200_with_booking_list(self, api_client, mock_use_cases):
        mock_use_cases.list_query.execute.return_value = [make_booking(record_id=1)]

        response = api_client.get("/api/v1/bookings/")

        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_query_params_forwarded_to_use_case(self, api_client, mock_use_cases):
        mock_use_cases.list_query.execute.return_value = []

        api_client.get("/api/v1/bookings/?start_date=2026-06-01&end_date=2026-06-30&limit=10")

        mock_use_cases.list_query.execute.assert_called_once_with(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 30),
            days=None,
            limit=10,
        )


# ---------------------------------------------------------------------------
# GET /api/v1/bookings/{id}
# ---------------------------------------------------------------------------


class TestGetBooking:
    def test_returns_200_with_correct_schema(self, api_client, mock_use_cases):
        booking = make_booking(
            record_id=5,
            apartment_id="B-2026-001",
            guest_name="María López",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
        )
        mock_use_cases.get_by_id_query.execute.return_value = booking

        response = api_client.get("/api/v1/bookings/5")

        assert response.status_code == 200
        data = response.json()
        assert data["record_id"] == 5
        assert data["apartment_id"] == "B-2026-001"
        assert data["guest_name"] == "María López"
        assert data["check_in"] == "2026-06-01"

    def test_returns_404_when_booking_not_found(self, api_client, mock_use_cases):
        mock_use_cases.get_by_id_query.execute.side_effect = BookingNotFound(99)

        response = api_client.get("/api/v1/bookings/99")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Endpoints de colecciones especiales
# ---------------------------------------------------------------------------


class TestSpecialCollectionEndpoints:
    def test_active_returns_200(self, api_client, mock_use_cases):
        mock_use_cases.get_active_query.execute.return_value = []

        assert api_client.get("/api/v1/bookings/active").status_code == 200

    def test_upcoming_checkouts_returns_200(self, api_client, mock_use_cases):
        mock_use_cases.upcoming_checkouts_query.execute.return_value = []

        assert api_client.get("/api/v1/bookings/upcoming-checkouts?days=7").status_code == 200

    def test_calendar_events_returns_200(self, api_client, mock_use_cases):
        mock_use_cases.calendar_events_query.execute.return_value = []

        assert api_client.get("/api/v1/bookings/calendar-events").status_code == 200


# ---------------------------------------------------------------------------
# POST /api/v1/bookings/
# ---------------------------------------------------------------------------


class TestCreateBooking:
    def test_valid_payload_returns_201(self, api_client, mock_use_cases):
        mock_use_cases.create_command.execute.return_value = make_booking(record_id=1)

        response = api_client.post(
            "/api/v1/bookings/",
            json={
                "apartment_id": "NEW-001",
                "guest_name": "Pedro Martínez",
                "check_in": "2026-07-01",
                "check_out": "2026-07-05",
                "nights": 4,
            },
        )

        assert response.status_code == 201

    def test_invalid_payload_returns_422(self, api_client):
        response = api_client.post(
            "/api/v1/bookings/",
            json={"guest_name": "Solo nombre"},  # falta apartment_id, check_in, check_out, nights
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/v1/bookings/{id}
# ---------------------------------------------------------------------------


class TestUpdateBooking:
    def test_valid_update_returns_200(self, api_client, mock_use_cases):
        mock_use_cases.update_command.execute.return_value = make_booking(
            record_id=1, guest_name="Nombre Nuevo"
        )

        response = api_client.put("/api/v1/bookings/1", json={"guest_name": "Nombre Nuevo"})

        assert response.status_code == 200

    def test_returns_404_when_not_found(self, api_client, mock_use_cases):
        mock_use_cases.update_command.execute.side_effect = BookingNotFound(99)

        response = api_client.put("/api/v1/bookings/99", json={"guest_name": "X"})

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/v1/bookings/{id}
# ---------------------------------------------------------------------------


class TestDeleteBooking:
    def test_deletes_and_returns_204(self, api_client, mock_use_cases):
        mock_use_cases.delete_command.execute.return_value = None

        response = api_client.delete("/api/v1/bookings/1")

        assert response.status_code == 204

    def test_returns_404_when_not_found(self, api_client, mock_use_cases):
        mock_use_cases.delete_command.execute.side_effect = BookingNotFound(99)

        response = api_client.delete("/api/v1/bookings/99")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Error handlers de dominio
# ---------------------------------------------------------------------------


class TestErrorHandlers:
    def test_booking_conflict_returns_409(self, api_client, mock_use_cases):
        mock_use_cases.create_command.execute.side_effect = BookingConflict(
            "2026-06-01", "2026-06-05"
        )

        response = api_client.post(
            "/api/v1/bookings/",
            json={
                "apartment_id": "CONFLICT",
                "guest_name": "Test",
                "check_in": "2026-06-01",
                "check_out": "2026-06-05",
                "nights": 4,
            },
        )

        assert response.status_code == 409

    def test_domain_validation_error_returns_422(self, api_client, mock_use_cases):
        mock_use_cases.create_command.execute.side_effect = DomainValidationError(
            "check_out debe ser posterior a check_in"
        )

        response = api_client.post(
            "/api/v1/bookings/",
            json={
                "apartment_id": "INVALID",
                "guest_name": "Test",
                "check_in": "2026-06-05",
                "check_out": "2026-06-10",
                "nights": 5,
            },
        )

        assert response.status_code == 422
