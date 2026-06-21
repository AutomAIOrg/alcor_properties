"""
Integration tests — endpoints HTTP de bookings.

FastAPI TestClient con use cases inyectados como MagicMock.
Sin base de datos real: la dependencia get_booking_use_cases se sobreescribe.
"""

from datetime import date

import pytest
from sqlalchemy.exc import SQLAlchemyError

from api.dependencies import get_current_user
from domain.auth.user_entity import Role
from domain.exceptions import BookingConflict, BookingNotFound, DomainValidationError
from main import app
from tests.helpers import make_booking, make_user

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
            apartment_id=None,
            status=None,
            guest_name=None,
            booking_number=None,
        )

    def test_start_date_only_is_allowed(self, api_client, mock_use_cases):
        mock_use_cases.list_query.execute.return_value = []

        response = api_client.get("/api/v1/bookings/?start_date=2026-06-01")

        assert response.status_code == 200
        mock_use_cases.list_query.execute.assert_called_once_with(
            start_date=date(2026, 6, 1),
            end_date=None,
            days=None,
            limit=None,
            apartment_id=None,
            status=None,
            guest_name=None,
            booking_number=None,
        )

    def test_returns_422_when_date_range_is_inverted(self, api_client, mock_use_cases):
        response = api_client.get("/api/v1/bookings/?start_date=2026-06-30&end_date=2026-06-01")

        assert response.status_code == 422
        assert "start_date debe ser anterior a end_date" in response.text
        mock_use_cases.list_query.execute.assert_not_called()

    def test_returns_422_when_days_is_not_positive(self, api_client, mock_use_cases):
        response = api_client.get("/api/v1/bookings/?start_date=2026-06-01&days=0")

        assert response.status_code == 422
        mock_use_cases.list_query.execute.assert_not_called()


# ---------------------------------------------------------------------------
# GET /api/v1/bookings/stats
# ---------------------------------------------------------------------------


class TestBookingStats:
    def test_start_date_only_is_allowed(self, api_client, mock_use_cases):
        mock_use_cases.stats_query.execute.return_value = {
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
            "status_breakdown": {},
            "start_date": date(2026, 6, 1),
            "end_date": None,
            "occupancy_pct": None,
        }

        response = api_client.get("/api/v1/bookings/stats?start_date=2026-06-01")

        assert response.status_code == 200
        mock_use_cases.stats_query.execute.assert_called_once_with(
            start_date=date(2026, 6, 1),
            end_date=None,
            days=None,
            apartment_id=None,
            status=None,
            guest_name=None,
            booking_number=None,
        )

    def test_returns_422_when_date_range_is_inverted(self, api_client, mock_use_cases):
        response = api_client.get(
            "/api/v1/bookings/stats?start_date=2026-06-30&end_date=2026-06-01"
        )

        assert response.status_code == 422
        assert "start_date debe ser anterior a end_date" in response.text
        mock_use_cases.stats_query.execute.assert_not_called()

    def test_returns_422_when_days_is_not_positive(self, api_client, mock_use_cases):
        response = api_client.get("/api/v1/bookings/stats?start_date=2026-06-01&days=0")

        assert response.status_code == 422
        mock_use_cases.stats_query.execute.assert_not_called()


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

    def test_cleaning_opportunities_returns_cleaning_window_schema(
        self, api_client, mock_use_cases
    ):
        from domain.bookings.entity import CleaningOpportunity

        mock_use_cases.get_cleaning_opportunities_query.execute.return_value = [
            CleaningOpportunity(
                source_booking_record_id=7,
                apartment_id="R180",
                available_from=date(2026, 6, 5),
                available_until=date(2026, 6, 10),
                comments="",
            )
        ]

        response = api_client.get("/api/v1/bookings/cleaning-opportunities")

        assert response.status_code == 200
        data = response.json()
        assert data == [
            {
                "source_booking_record_id": 7,
                "apartment_id": "R180",
                "available_from": "2026-06-05",
                "available_until": "2026-06-10",
                "comments": "",
                "has_bill": False,
                "can_bill": False,
                "bill_state": None,
            }
        ]
        mock_use_cases.get_cleaning_opportunities_query.execute.assert_called_once_with()
        mock_use_cases.get_by_id_query.execute.assert_not_called()

    def test_cleaning_opportunities_allows_limpiadora_role(self, api_client, mock_use_cases):
        mock_use_cases.get_cleaning_opportunities_query.execute.return_value = []
        cleaner_user = make_user(
            id=2,
            username="limpiadora",
            name="Limpiadora",
            role=Role.LIMPIADORA,
        )
        app.dependency_overrides[get_current_user] = lambda: cleaner_user

        try:
            response = api_client.get("/api/v1/bookings/cleaning-opportunities")
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 200
        assert response.json() == []
        mock_use_cases.get_cleaning_opportunities_query.execute.assert_called_once_with()


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
        _, update_data = mock_use_cases.update_command.execute.call_args.args
        assert update_data.as_update_dict() == {"guest_name": "Nombre Nuevo"}

    def test_update_forwards_explicit_null_for_optional_fields(self, api_client, mock_use_cases):
        mock_use_cases.update_command.execute.return_value = make_booking(record_id=1, email=None)

        response = api_client.put("/api/v1/bookings/1", json={"email": None})

        assert response.status_code == 200
        _, update_data = mock_use_cases.update_command.execute.call_args.args
        assert update_data.as_update_dict() == {"email": None}

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
