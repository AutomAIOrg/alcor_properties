"""
Integration tests — endpoints HTTP de bills.

FastAPI TestClient con casos de uso inyectados como MagicMock.
"""

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest
from starlette.testclient import TestClient

from api.dependencies import get_current_user
from domain.auth.user_entity import Role
from domain.bills.entity import BILL_STATE_PENDING
from domain.exceptions import (
    BillAlreadyExistsError,
    BillNotFoundError,
    BookingNotFound,
    DomainValidationError,
)
from main import app
from tests.helpers import make_bill, make_user

pytestmark = pytest.mark.integration

_VALID_PAYLOAD = {
    "record_id": 5,
    "cleaning_date": "2026-06-01",
    "start_time": "10:00",
    "end_time": "12:00",
    "cleaning_type_id": 1,
}


class TestCreateBill:
    def test_valid_payload_returns_201(self, bills_api_client, mock_create_bill_use_case):
        mock_create_bill_use_case.execute.return_value = make_bill(bill_id=1)

        response = bills_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)

        assert response.status_code == 201
        data = response.json()
        assert data["bill_id"] == 1
        assert data["state"] == "Creada"
        mock_create_bill_use_case.execute.assert_called_once()

    def test_missing_required_field_returns_422(self, bills_api_client):
        response = bills_api_client.post("/api/v1/bills/", json={"record_id": 5})

        assert response.status_code == 422


class TestUpdateBillState:
    def test_mark_as_paid_returns_200(self, bills_api_client, mock_update_bill_state_use_case):
        mock_update_bill_state_use_case.execute.return_value = make_bill(
            bill_id=1, state="Pagada", paid_at=date(2026, 6, 1)
        )

        response = bills_api_client.put(
            "/api/v1/bills/1", json={"state": "Pagada", "paid_at": "2026-06-01"}
        )

        assert response.status_code == 200
        assert response.json()["state"] == "Pagada"
        # El cliente de pruebas autentica como limpiadora: el usuario completo viaja
        # al caso de uso para registrar quién confirmó el pago (rol, nombre y apellidos).
        mock_update_bill_state_use_case.execute.assert_called_once()
        call = mock_update_bill_state_use_case.execute.call_args
        assert call.args == (1, "Pagada")
        assert call.kwargs["actor"].role == Role.LIMPIADORA
        assert call.kwargs["actor"].name == "Limpiadora"
        assert call.kwargs["actor"].lastname == "Test"
        assert call.kwargs["paid_at"] == date(2026, 6, 1)
        assert call.kwargs["cancellation_note"] is None

    def test_partial_confirmation_returns_confirmation_fields(
        self, bills_api_client, mock_update_bill_state_use_case
    ):
        mock_update_bill_state_use_case.execute.return_value = make_bill(
            bill_id=1, state="Creada", paid_confirmed_by_cleaner=datetime(2026, 6, 1, 14, 30)
        )

        response = bills_api_client.put(
            "/api/v1/bills/1", json={"state": "Pagada", "paid_at": "2026-06-01"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "Creada"
        assert data["paid_confirmed_by_cleaner"] == "2026-06-01T14:30:00"
        assert data["paid_confirmed_by_admin"] is None

    def test_cancel_with_note_passes_note_to_use_case(
        self, bills_api_client, mock_update_bill_state_use_case
    ):
        mock_update_bill_state_use_case.execute.return_value = make_bill(
            bill_id=1, state="Cancelada", cancellation_note="Reserva duplicada"
        )

        response = bills_api_client.put(
            "/api/v1/bills/1",
            json={"state": "Cancelada", "cancellation_note": "Reserva duplicada"},
        )

        assert response.status_code == 200
        assert response.json()["cancellation_note"] == "Reserva duplicada"
        call = mock_update_bill_state_use_case.execute.call_args
        assert call.args == (1, "Cancelada")
        assert call.kwargs["actor"].role == Role.LIMPIADORA
        assert call.kwargs["paid_at"] is None
        assert call.kwargs["cancellation_note"] == "Reserva duplicada"

    def test_invalid_transition_returns_422(
        self, bills_api_client, mock_update_bill_state_use_case
    ):
        mock_update_bill_state_use_case.execute.side_effect = DomainValidationError(
            "transición inválida"
        )

        response = bills_api_client.put("/api/v1/bills/1", json={"state": "Cancelada"})

        assert response.status_code == 422

    def test_missing_bill_returns_404(self, bills_api_client, mock_update_bill_state_use_case):
        mock_update_bill_state_use_case.execute.side_effect = BillNotFoundError(99)

        response = bills_api_client.put("/api/v1/bills/99", json={"state": "Pagada"})

        assert response.status_code == 404


class TestListBills:
    def test_without_state_composes_pending_and_real(
        self,
        bills_api_client,
        mock_list_bills_use_case,
        mock_list_pending_bills_use_case,
    ):
        pending = make_bill(bill_id=None, state=BILL_STATE_PENDING, record_id=10)
        real = make_bill(bill_id=1, state="Creada", record_id=5)
        mock_list_pending_bills_use_case.execute.return_value = [pending]
        mock_list_bills_use_case.execute.return_value = [real]

        response = bills_api_client.get("/api/v1/bills/")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["state"] == BILL_STATE_PENDING
        assert data[1]["bill_id"] == 1

    def test_with_pending_state_returns_only_pending(
        self,
        bills_api_client,
        mock_list_bills_use_case,
        mock_list_pending_bills_use_case,
    ):
        pending = make_bill(bill_id=None, state=BILL_STATE_PENDING)
        mock_list_pending_bills_use_case.execute.return_value = [pending]

        response = bills_api_client.get("/api/v1/bills/", params={"state": BILL_STATE_PENDING})

        assert response.status_code == 200
        assert len(response.json()) == 1
        mock_list_bills_use_case.execute.assert_not_called()


class TestErrorHandlers:
    def test_bill_already_exists_returns_409(self, bills_api_client, mock_create_bill_use_case):
        mock_create_bill_use_case.execute.side_effect = BillAlreadyExistsError(5)

        response = bills_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)

        assert response.status_code == 409

    def test_booking_not_found_returns_404(self, bills_api_client, mock_create_bill_use_case):
        mock_create_bill_use_case.execute.side_effect = BookingNotFound(99)

        response = bills_api_client.post(
            "/api/v1/bills/",
            json={**_VALID_PAYLOAD, "record_id": 99},
        )

        assert response.status_code == 404

    def test_cancelled_booking_returns_422(self, bills_api_client, mock_create_bill_use_case):
        mock_create_bill_use_case.execute.side_effect = DomainValidationError(
            "No se puede facturar una reserva cancelada."
        )

        response = bills_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)

        assert response.status_code == 422
        assert "cancelada" in response.json()["detail"]

    def test_booking_not_yet_cleanable_returns_422(
        self, bills_api_client, mock_create_bill_use_case
    ):
        mock_create_bill_use_case.execute.side_effect = DomainValidationError(
            "La limpieza aún no puede facturarse: el check-out no ha ocurrido."
        )

        response = bills_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)

        assert response.status_code == 422
        assert "check-out" in response.json()["detail"]


class TestPermissions:
    def test_admin_can_create_bill(self, bills_api_client, mock_create_bill_use_case):
        admin_user = make_user(role=Role.ADMIN)
        app.dependency_overrides[get_current_user] = lambda: admin_user
        mock_create_bill_use_case.execute.return_value = make_bill(bill_id=1)

        try:
            response = bills_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 201

    def test_unauthenticated_request_returns_401(self):
        from api.dependencies import (
            get_create_bill_use_case,
            get_list_bills_use_case,
            get_list_pending_bills_use_case,
            get_update_bill_state_use_case,
        )

        deps = (
            get_create_bill_use_case,
            get_update_bill_state_use_case,
            get_list_bills_use_case,
            get_list_pending_bills_use_case,
            get_current_user,
        )
        saved_overrides = dict(app.dependency_overrides)
        try:
            for dep in deps:
                app.dependency_overrides.pop(dep, None)

            with TestClient(app, raise_server_exceptions=False) as client:
                response = client.post("/api/v1/bills/", json=_VALID_PAYLOAD)
        finally:
            app.dependency_overrides.clear()
            app.dependency_overrides.update(saved_overrides)

        assert response.status_code == 401

    def test_non_cleaning_role_returns_403(self, bills_api_client, mock_create_bill_use_case):
        unauthorized = MagicMock()
        unauthorized.role = "guest"
        app.dependency_overrides[get_current_user] = lambda: unauthorized
        mock_create_bill_use_case.execute.return_value = make_bill(bill_id=1)

        try:
            response = bills_api_client.post("/api/v1/bills/", json=_VALID_PAYLOAD)
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        assert response.status_code == 403
