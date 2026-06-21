"""
Integration tests — endpoints HTTP de bills.

FastAPI TestClient con use cases inyectados como MagicMock.
Sin base de datos real: la dependencia get_bill_use_cases se sobreescribe.
"""

from datetime import date

import pytest

from api.dependencies import get_current_user
from domain.auth.user_entity import Role
from domain.exceptions import BillAlreadyExists, BookingNotFound, DomainValidationError
from main import app
from tests.helpers import make_bill, make_user

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# POST /api/v1/bills/
# ---------------------------------------------------------------------------


_VALID_PAYLOAD = {
    "record_id": 5,
    "cleaning_date": "2026-06-01",
    "start_time": "10:00",
    "end_time": "12:00",
}


class TestCreateBill:
    def test_valid_payload_returns_201(self, bill_api_client, mock_bill_use_cases):
        mock_bill_use_cases.create_command.execute.return_value = make_bill(bill_id=1)

        response = bill_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)

        assert response.status_code == 201
        data = response.json()
        assert data["bill_id"] == 1
        assert data["apartment_id"] == "TEST-001"
        assert data["state"] == "Creada"
        mock_bill_use_cases.create_command.execute.assert_called_once()

    def test_missing_required_field_returns_422(self, bill_api_client):
        response = bill_api_client.post(
            "/api/v1/bills/",
            json={"record_id": 5},  # falta cleaning_date, start_time, end_time
        )

        assert response.status_code == 422

    def test_invalid_date_format_returns_422(self, bill_api_client):
        response = bill_api_client.post(
            "/api/v1/bills/",
            json={**_VALID_PAYLOAD, "cleaning_date": "not-a-date"},
        )

        assert response.status_code == 422

    def test_invalid_time_format_returns_422(self, bill_api_client):
        response = bill_api_client.post(
            "/api/v1/bills/",
            json={**_VALID_PAYLOAD, "start_time": "not-a-time"},
        )

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/v1/bills/{id}
# ---------------------------------------------------------------------------


class TestUpdateBillState:
    def test_mark_as_paid_returns_200(self, bill_api_client, mock_bill_use_cases):
        mock_bill_use_cases.update_state_command.execute.return_value = make_bill(
            bill_id=1, state="Pagada", paid_at=date(2026, 6, 1)
        )

        response = bill_api_client.patch(
            "/api/v1/bills/1", json={"state": "Pagada", "paid_at": "2026-06-01"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "Pagada"
        assert data["paid_at"] == "2026-06-01"
        mock_bill_use_cases.update_state_command.execute.assert_called_once_with(
            1, "Pagada", paid_at=date(2026, 6, 1)
        )

    def test_invalid_transition_returns_422(self, bill_api_client, mock_bill_use_cases):
        mock_bill_use_cases.update_state_command.execute.side_effect = DomainValidationError(
            "transición inválida"
        )

        response = bill_api_client.patch("/api/v1/bills/1", json={"state": "Cancelada"})

        assert response.status_code == 422

    def test_missing_bill_returns_404(self, bill_api_client, mock_bill_use_cases):
        from domain.exceptions import BillNotFound

        mock_bill_use_cases.update_state_command.execute.side_effect = BillNotFound(99)

        response = bill_api_client.patch("/api/v1/bills/99", json={"state": "Pagada"})

        assert response.status_code == 404

    def test_missing_state_returns_422(self, bill_api_client):
        response = bill_api_client.patch("/api/v1/bills/1", json={})

        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Error handlers de dominio
# ---------------------------------------------------------------------------


class TestErrorHandlers:
    def test_bill_already_exists_returns_409(self, bill_api_client, mock_bill_use_cases):
        mock_bill_use_cases.create_command.execute.side_effect = BillAlreadyExists(5)

        response = bill_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)

        assert response.status_code == 409
        assert "factura" in response.json()["detail"].lower()

    def test_booking_not_found_returns_404(self, bill_api_client, mock_bill_use_cases):
        mock_bill_use_cases.create_command.execute.side_effect = BookingNotFound(99)

        response = bill_api_client.post(
            "/api/v1/bills/",
            json={**_VALID_PAYLOAD, "record_id": 99},
        )

        assert response.status_code == 404

    def test_domain_validation_error_returns_422(self, bill_api_client, mock_bill_use_cases):
        mock_bill_use_cases.create_command.execute.side_effect = DomainValidationError(
            "La hora de fin debe ser posterior a la hora de inicio."
        )

        response = bill_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)

        assert response.status_code == 422
        assert "hora" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Permisos — require_cleaning
# ---------------------------------------------------------------------------


class TestPermissions:
    def test_admin_can_create_bill(self, bill_api_client, mock_bill_use_cases):
        admin_user = make_user(role=Role.ADMIN)
        app.dependency_overrides[get_current_user] = lambda: admin_user
        mock_bill_use_cases.create_command.execute.return_value = make_bill(bill_id=1)

        try:
            response = bill_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 201

    def test_limpiadora_can_create_bill(self, bill_api_client, mock_bill_use_cases):
        mock_bill_use_cases.create_command.execute.return_value = make_bill(bill_id=1)

        response = bill_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)

        assert response.status_code == 201

    def test_unauthenticated_request_returns_401(self):
        from starlette.testclient import TestClient

        from api.dependencies import get_bill_use_cases

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_bill_use_cases, None)

        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post("/api/v1/bills/", json=_VALID_PAYLOAD)
        finally:
            pass

        assert response.status_code == 401
