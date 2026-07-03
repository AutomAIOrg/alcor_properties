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


def _create_cleaning_type(
    e2e_client, admin_auth_headers, name: str = "Limpieza normal", rate: str = "18.00"
) -> int:
    r = e2e_client.post(
        "/api/v1/cleaning-types/",
        json={"name": name, "hourly_rate": rate},
        headers=admin_auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["cleaning_type_id"]


def _bill_payload(record_id: int, cleaning_type_id: int, cleaning_date: str = "2026-06-02") -> dict:
    return {
        "record_id": record_id,
        "cleaning_date": cleaning_date,
        "start_time": "10:00",
        "end_time": "12:00",
        "cleaning_type_id": cleaning_type_id,
    }


def _create_booking_and_bill(e2e_client, admin_auth_headers, apartment_suffix: str = "") -> int:
    payload = _BOOKING_PAYLOAD
    if apartment_suffix:
        payload = {**_BOOKING_PAYLOAD, "apartment_id": f"E2E-BILL-{apartment_suffix}"}
    r = e2e_client.post("/api/v1/bookings/", json=payload, headers=admin_auth_headers)
    assert r.status_code == 201
    record_id = r.json()["record_id"]
    cleaning_type_id = _create_cleaning_type(
        e2e_client, admin_auth_headers, name=f"Tipo {apartment_suffix or 'base'}"
    )
    r = e2e_client.post(
        "/api/v1/bills/",
        json=_bill_payload(record_id, cleaning_type_id),
        headers=admin_auth_headers,
    )
    assert r.status_code == 201
    return r.json()["bill_id"]


class TestCleaningTypeDrivenBillCreation:
    def test_bill_uses_selected_cleaning_type_rate(self, e2e_client, admin_auth_headers):
        cleaning_type_id = _create_cleaning_type(
            e2e_client, admin_auth_headers, name="Limpieza fin de semana", rate="18.00"
        )

        r = e2e_client.post(
            "/api/v1/bookings/",
            json=_BOOKING_PAYLOAD,
            headers=admin_auth_headers,
        )
        assert r.status_code == 201
        record_id = r.json()["record_id"]

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id, cleaning_type_id),
            headers=admin_auth_headers,
        )

        assert r.status_code == 201
        data = r.json()
        assert data["hourly_rate"] == 18.0
        assert data["clean_hours"] == 2.0
        assert data["cost"] == 36.0
        assert data["cleaning_type_id"] == cleaning_type_id
        assert data["cleaning_type_name"] == "Limpieza fin de semana"
        assert data["state"] == "Creada"


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
        cleaning_type_id = _create_cleaning_type(e2e_client, admin_auth_headers, name="Tipo dup")

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id, cleaning_type_id),
            headers=admin_auth_headers,
        )
        assert r.status_code == 201

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id, cleaning_type_id),
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
        cleaning_type_id = _create_cleaning_type(e2e_client, admin_auth_headers, name="Tipo time")

        r = e2e_client.post(
            "/api/v1/bills/",
            json={
                "record_id": record_id,
                "cleaning_date": "2026-06-02",
                "start_time": "14:00",
                "end_time": "10:00",
                "cleaning_type_id": cleaning_type_id,
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
        cleaning_type_id = _create_cleaning_type(e2e_client, admin_auth_headers, name="Tipo cancel")

        r = e2e_client.put(
            f"/api/v1/bookings/{record_id}",
            json={"status": "cancelled"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id, cleaning_type_id),
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
        cleaning_type_id = _create_cleaning_type(e2e_client, admin_auth_headers, name="Tipo future")

        r = e2e_client.post(
            "/api/v1/bills/",
            json=_bill_payload(record_id, cleaning_type_id, cleaning_date="2026-07-15"),
            headers=admin_auth_headers,
        )
        assert r.status_code == 422
        assert "check-out" in r.json()["detail"]
