"""
End-to-end tests — flujos completos de facturas sin mocks.

Stack: TestClient → Use Cases reales → SQLAlchemy Repositories → SQLite en memoria.
"""

import pytest

pytestmark = pytest.mark.e2e

_BOOKING_PAYLOAD = {
    "apartment_id": "E2E-BILL-001",
    "guest_name": "Huésped Factura E2E",
    "check_in": "2026-05-28",
    "check_out": "2026-06-02",
    "nights": 5,
    "persons": 2,
    "adults": 2,
    "children": 0,
}


def _bill_payload(record_id: int, cleaning_date: str = "2026-06-02") -> dict:
    return {
        "record_id": record_id,
        "cleaning_date": cleaning_date,
        "start_time": "10:00",
        "end_time": "12:00",
    }


def _create_booking_and_bill(e2e_client, admin_auth_headers, apartment_suffix: str = "") -> int:
    payload = _BOOKING_PAYLOAD
    if apartment_suffix:
        payload = {**_BOOKING_PAYLOAD, "apartment_id": f"E2E-BILL-{apartment_suffix}"}
    r = e2e_client.post("/api/v1/bookings/", json=payload, headers=admin_auth_headers)
    assert r.status_code == 201
    record_id = r.json()["record_id"]
    r = e2e_client.post(
        "/api/v1/bills/",
        json=_bill_payload(record_id),
        headers=admin_auth_headers,
    )
    assert r.status_code == 201
    return r.json()["bill_id"]


class TestSettingsDrivenBillCreation:
    def test_admin_updates_rate_and_bill_uses_persisted_rate(self, e2e_client, admin_auth_headers):
        r = e2e_client.put(
            "/api/v1/settings/cleaning-rate",
            json={"cleaning_hourly_rate": "18.00"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["cleaning_hourly_rate"] == 18.0

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
        assert data["hourly_rate"] == 18.0
        assert data["clean_hours"] == 2.0
        assert data["cost"] == 36.0
        assert data["state"] == "Creada"

        r = e2e_client.get(
            "/api/v1/settings/cleaning-rate",
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["cleaning_hourly_rate"] == 18.0


class TestBillStateLifecycle:
    def test_full_state_cycle(self, e2e_client, admin_auth_headers):
        bill_id = _create_booking_and_bill(e2e_client, admin_auth_headers, "STATE-001")

        r = e2e_client.put(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Pagada", "paid_at": "2026-08-06"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["state"] == "Pagada"
        assert r.json()["paid_at"] == "2026-08-06"

        r = e2e_client.put(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Creada"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["paid_at"] is None

        r = e2e_client.put(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Cancelada"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["state"] == "Cancelada"

        r = e2e_client.put(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Creada"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["state"] == "Creada"

    def test_cancel_with_note_stores_and_clears_on_reactivation(
        self, e2e_client, admin_auth_headers
    ):
        bill_id = _create_booking_and_bill(e2e_client, admin_auth_headers, "STATE-NOTE-001")

        r = e2e_client.put(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Cancelada", "cancellation_note": "Reserva duplicada"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["state"] == "Cancelada"
        assert r.json()["cancellation_note"] == "Reserva duplicada"

        # Al reactivar la factura, la nota se limpia.
        r = e2e_client.put(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Creada"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["cancellation_note"] is None

    def test_invalid_transition_returns_422(self, e2e_client, admin_auth_headers):
        bill_id = _create_booking_and_bill(e2e_client, admin_auth_headers, "STATE-002")

        e2e_client.put(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Pagada"},
            headers=admin_auth_headers,
        )

        r = e2e_client.put(
            f"/api/v1/bills/{bill_id}",
            json={"state": "Cancelada"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 422


class TestDuplicateBillFlow:
    def test_second_bill_for_same_booking_returns_409(self, e2e_client, admin_auth_headers):
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


class TestTimeValidationFlow:
    def test_end_before_start_returns_422(self, e2e_client, admin_auth_headers):
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
                "cleaning_date": "2026-06-02",
                "start_time": "14:00",
                "end_time": "10:00",
            },
            headers=admin_auth_headers,
        )
        assert r.status_code == 422


class TestBillabilityValidation:
    def test_cancelled_booking_returns_422(self, e2e_client, admin_auth_headers):
        r = e2e_client.post(
            "/api/v1/bookings/",
            json={**_BOOKING_PAYLOAD, "apartment_id": "E2E-CANCEL-001"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 201
        record_id = r.json()["record_id"]

        r = e2e_client.put(
            f"/api/v1/bookings/{record_id}",
            json={"status": "cancelled"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id),
            headers=admin_auth_headers,
        )
        assert r.status_code == 422
        assert "cancelada" in r.json()["detail"]

    def test_future_checkout_returns_422(self, e2e_client, admin_auth_headers):
        r = e2e_client.post(
            "/api/v1/bookings/",
            json={
                **_BOOKING_PAYLOAD,
                "apartment_id": "E2E-FUTURE-001",
                "check_in": "2026-07-10",
                "check_out": "2026-07-15",
                "nights": 5,
            },
            headers=admin_auth_headers,
        )
        assert r.status_code == 201
        record_id = r.json()["record_id"]

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id, cleaning_date="2026-07-15"),
            headers=admin_auth_headers,
        )
        assert r.status_code == 422
        assert "check-out" in r.json()["detail"]
