"""
End-to-end tests — flujos completos de facturas sin mocks.

Stack: TestClient → Use Cases reales → SQLAlchemy Repositories → SQLite en memoria.
Solo se sobreescribe get_db para apuntar a SQLite en lugar de MySQL.
"""

from decimal import Decimal

import pytest

from config import settings

pytestmark = pytest.mark.e2e


_BOOKING_PAYLOAD = {
    "apartment_id": "E2E-BILL-001",
    "guest_name": "Huésped Factura E2E",
    "check_in": "2026-08-01",
    "check_out": "2026-08-05",
    "nights": 4,
    "persons": 2,
    "adults": 2,
    "children": 0,
}


def _bill_payload(record_id: int) -> dict:
    return {
        "record_id": record_id,
        "cleaning_date": "2026-08-05",
        "start_time": "10:00",
        "end_time": "12:00",
    }


# ---------------------------------------------------------------------------
# Flujo de creación completo
# ---------------------------------------------------------------------------


class TestCreateBillFlow:
    def test_create_bill_derives_fields_from_booking(
        self, e2e_client, admin_auth_headers, monkeypatch
    ):
        monkeypatch.setattr(settings, "CLEANING_HOURLY_RATE", Decimal("15"))

        r = e2e_client.post(
            "/api/v1/bookings/",
            json=_BOOKING_PAYLOAD,
            headers=admin_auth_headers,
        )
        assert r.status_code == 201
        record_id = r.json()["record_id"]

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id),
            headers=admin_auth_headers,
        )

        assert r.status_code == 201
        data = r.json()
        assert data["bill_id"] is not None
        assert data["record_id"] == record_id
        assert data["apartment_id"] == "E2E-BILL-001"
        assert data["clean_hours"] == 2.0
        assert data["cost"] == 30.0  # 2h × 15€
        assert data["state"] == "Creada"
        assert data["cleaning_date"] == "2026-08-05"
        assert data["paid_at"] is None


# ---------------------------------------------------------------------------
# Ciclo de estados: Creada → Pagada → Creada → Cancelada → Creada
# ---------------------------------------------------------------------------


class TestBillStateLifecycle:
    def test_full_state_cycle(self, e2e_client, admin_auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "CLEANING_HOURLY_RATE", Decimal("15"))

        r = e2e_client.post(
            "/api/v1/bookings/",
            json={**_BOOKING_PAYLOAD, "apartment_id": "E2E-STATE-001"},
            headers=admin_auth_headers,
        )
        record_id = r.json()["record_id"]
        r = e2e_client.post(
            "/api/v1/bills/", json=_bill_payload(record_id), headers=admin_auth_headers
        )
        bill_id = r.json()["bill_id"]

        # Creada → Pagada con fecha explícita
        r = e2e_client.patch(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Pagada", "paid_at": "2026-08-06"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["state"] == "Pagada"
        assert r.json()["paid_at"] == "2026-08-06"

        # Pagada → Creada limpia la fecha de pago
        r = e2e_client.patch(
            f"/api/v1/bills/{bill_id}", json={"state": "Creada"}, headers=admin_auth_headers
        )
        assert r.status_code == 200
        assert r.json()["paid_at"] is None

        # Creada → Cancelada
        r = e2e_client.patch(
            f"/api/v1/bills/{bill_id}", json={"state": "Cancelada"}, headers=admin_auth_headers
        )
        assert r.status_code == 200
        assert r.json()["state"] == "Cancelada"

        # Cancelada → Creada (reactivar)
        r = e2e_client.patch(
            f"/api/v1/bills/{bill_id}", json={"state": "Creada"}, headers=admin_auth_headers
        )
        assert r.status_code == 200
        assert r.json()["state"] == "Creada"

    def test_invalid_transition_returns_422(self, e2e_client, admin_auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "CLEANING_HOURLY_RATE", Decimal("15"))

        r = e2e_client.post(
            "/api/v1/bookings/",
            json={**_BOOKING_PAYLOAD, "apartment_id": "E2E-STATE-002"},
            headers=admin_auth_headers,
        )
        record_id = r.json()["record_id"]
        r = e2e_client.post(
            "/api/v1/bills/", json=_bill_payload(record_id), headers=admin_auth_headers
        )
        bill_id = r.json()["bill_id"]

        e2e_client.patch(
            f"/api/v1/bills/{bill_id}", json={"state": "Pagada"}, headers=admin_auth_headers
        )

        # Pagada → Cancelada no está permitido directamente
        r = e2e_client.patch(
            f"/api/v1/bills/{bill_id}", json={"state": "Cancelada"}, headers=admin_auth_headers
        )
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Invariante: una factura por reserva
# ---------------------------------------------------------------------------


class TestDuplicateBillFlow:
    def test_second_bill_for_same_booking_returns_409(
        self, e2e_client, admin_auth_headers, monkeypatch
    ):
        monkeypatch.setattr(settings, "CLEANING_HOURLY_RATE", Decimal("15"))

        r = e2e_client.post(
            "/api/v1/bookings/",
            json={**_BOOKING_PAYLOAD, "apartment_id": "E2E-DUP-001"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 201
        record_id = r.json()["record_id"]

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id),
            headers=admin_auth_headers,
        )
        assert r.status_code == 201

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id),
            headers=admin_auth_headers,
        )

        assert r.status_code == 409


# ---------------------------------------------------------------------------
# Reserva inexistente
# ---------------------------------------------------------------------------


class TestBookingNotFoundFlow:
    def test_bill_for_nonexistent_booking_returns_404(
        self, e2e_client, admin_auth_headers, monkeypatch
    ):
        monkeypatch.setattr(settings, "CLEANING_HOURLY_RATE", Decimal("15"))

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(99999),
            headers=admin_auth_headers,
        )

        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Validación de horarios
# ---------------------------------------------------------------------------


class TestTimeValidationFlow:
    def test_end_before_start_returns_422(self, e2e_client, admin_auth_headers, monkeypatch):
        monkeypatch.setattr(settings, "CLEANING_HOURLY_RATE", Decimal("15"))

        r = e2e_client.post(
            "/api/v1/bookings/",
            json={**_BOOKING_PAYLOAD, "apartment_id": "E2E-TIME-001"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 201
        record_id = r.json()["record_id"]

        r = e2e_client.post(
            "/api/v1/bills/",
            json={
                "record_id": record_id,
                "cleaning_date": "2026-08-05",
                "start_time": "14:00",
                "end_time": "10:00",
            },
            headers=admin_auth_headers,
        )

        assert r.status_code == 422
