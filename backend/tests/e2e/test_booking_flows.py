"""
End-to-end tests — flujos completos sin mocks.

Stack: TestClient → Use Cases reales → SQLAlchemyBookingRepository → SQLite en memoria.
Solo se sobreescribe get_db para apuntar a SQLite en lugar de MySQL.
"""

import pytest
from datetime import date, timedelta

pytestmark = pytest.mark.e2e

# Payload reutilizable para crear una reserva válida
_BASE_PAYLOAD = {
    "booking_id": "E2E-001",
    "guest_name": "Pedro E2E",
    "check_in": "2026-08-01",
    "check_out": "2026-08-05",
    "nights": 4,
    "persons": 2,
    "adults": 2,
    "children": 0,
}


# ---------------------------------------------------------------------------
# Ciclo CRUD completo
# ---------------------------------------------------------------------------


class TestCrudFlow:
    def test_create_get_update_delete_cycle(self, e2e_client):
        # Crear
        r = e2e_client.post("/api/v1/bookings/", json=_BASE_PAYLOAD)
        assert r.status_code == 201
        record_id = r.json()["record_id"]
        assert record_id is not None

        # Obtener
        r = e2e_client.get(f"/api/v1/bookings/{record_id}")
        assert r.status_code == 200
        assert r.json()["guest_name"] == "Pedro E2E"

        # Actualizar
        r = e2e_client.put(
            f"/api/v1/bookings/{record_id}",
            json={"guest_name": "Pedro E2E Actualizado"},
        )
        assert r.status_code == 200
        assert r.json()["guest_name"] == "Pedro E2E Actualizado"

        # Eliminar
        r = e2e_client.delete(f"/api/v1/bookings/{record_id}")
        assert r.status_code == 204

        # Confirmar eliminación
        r = e2e_client.get(f"/api/v1/bookings/{record_id}")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Flujo de reservas activas
# ---------------------------------------------------------------------------


class TestActiveBookingsFlow:
    def test_booking_covering_today_appears_in_active_list(self, e2e_client):
        today = date.today()
        payload = {
            "booking_id": "ACTIVE-E2E",
            "guest_name": "Huésped Activo",
            "check_in": (today - timedelta(days=1)).isoformat(),
            "check_out": (today + timedelta(days=2)).isoformat(),
            "nights": 3,
        }

        e2e_client.post("/api/v1/bookings/", json=payload)
        r = e2e_client.get("/api/v1/bookings/active")

        assert r.status_code == 200
        guest_names = [b["guest_name"] for b in r.json()]
        assert "Huésped Activo" in guest_names


# ---------------------------------------------------------------------------
# Flujo de calendario
# ---------------------------------------------------------------------------


class TestCalendarFlow:
    def test_confirmed_booking_appears_in_calendar_events(self, e2e_client):
        payload = {**_BASE_PAYLOAD, "booking_id": "CAL-E2E", "status": "Confirmed"}
        e2e_client.post("/api/v1/bookings/", json=payload)

        r = e2e_client.get("/api/v1/bookings/calendar-events?start_date=2026-07-01&days=60")

        assert r.status_code == 200
        booking_ids = [ev["extendedProps"]["booking_id"] for ev in r.json()]
        assert "CAL-E2E" in booking_ids

    def test_recently_cancelled_booking_excluded_from_calendar(self, e2e_client):
        today = date.today()
        cancelled_payload = {
            "booking_id": "CANCELLED-E2E",
            "guest_name": "Cancelado",
            "check_in": (today + timedelta(days=1)).isoformat(),
            "check_out": (today + timedelta(days=4)).isoformat(),
            "nights": 3,
            "status": "Cancelled",
        }
        e2e_client.post("/api/v1/bookings/", json=cancelled_payload)

        r = e2e_client.get(
            f"/api/v1/bookings/calendar-events?start_date={today.isoformat()}&days=30"
        )

        assert r.status_code == 200
        booking_ids = [ev["extendedProps"]["booking_id"] for ev in r.json()]
        assert "CANCELLED-E2E" not in booking_ids


# ---------------------------------------------------------------------------
# Bonificación eléctrica end-to-end
# ---------------------------------------------------------------------------


class TestElectricAllowanceFlow:
    def test_electric_allowance_calculated_when_booking_id_in_electric_setting(
        self, e2e_client, monkeypatch
    ):
        from config import settings

        monkeypatch.setattr(settings, "ELECTRIC", "ELEC-E2E-001")

        payload = {
            "booking_id": "ELEC-E2E-001",
            "guest_name": "Huésped Eléctrico",
            "check_in": "2026-09-01",
            "check_out": "2026-09-04",
            "nights": 3,
        }

        r = e2e_client.post("/api/v1/bookings/", json=payload)

        assert r.status_code == 201
        data = r.json()
        assert data["electric_allowance"] == 3 * 4.0
