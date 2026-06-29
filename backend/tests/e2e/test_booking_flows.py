"""
End-to-end tests — flujos completos sin mocks.

Stack: TestClient → Use Cases reales → SQLAlchemyBookingRepository → SQLite en memoria.
Solo se sobreescribe get_db para apuntar a SQLite en lugar de MySQL.
"""

from datetime import date, timedelta

import pytest

pytestmark = pytest.mark.e2e

# Payload reutilizable para crear una reserva válida
_BASE_PAYLOAD = {
    "apartment_id": "E2E-001",
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
    def test_create_get_update_delete_cycle(self, e2e_client, admin_auth_headers):
        # Crear
        r = e2e_client.post(
            "/api/v1/bookings/",
            json=_BASE_PAYLOAD,
            headers=admin_auth_headers,
        )
        assert r.status_code == 201
        record_id = r.json()["record_id"]
        assert record_id is not None

        # Obtener
        r = e2e_client.get(f"/api/v1/bookings/{record_id}", headers=admin_auth_headers)
        assert r.status_code == 200
        assert r.json()["guest_name"] == "Pedro E2E"

        # Actualizar
        r = e2e_client.put(
            f"/api/v1/bookings/{record_id}",
            json={"guest_name": "Pedro E2E Actualizado"},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["guest_name"] == "Pedro E2E Actualizado"

        # Eliminar
        r = e2e_client.delete(f"/api/v1/bookings/{record_id}", headers=admin_auth_headers)
        assert r.status_code == 204

        # Confirmar eliminación
        r = e2e_client.get(f"/api/v1/bookings/{record_id}", headers=admin_auth_headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Flujo de reservas activas
# ---------------------------------------------------------------------------


class TestActiveBookingsFlow:
    def test_booking_covering_today_appears_in_active_list(self, e2e_client, admin_auth_headers):
        today = date.today()
        payload = {
            "apartment_id": "ACTIVE-E2E",
            "guest_name": "Huésped Activo",
            "check_in": (today - timedelta(days=1)).isoformat(),
            "check_out": (today + timedelta(days=2)).isoformat(),
            "nights": 3,
        }

        e2e_client.post(
            "/api/v1/bookings/",
            json=payload,
            headers=admin_auth_headers,
        )
        r = e2e_client.get("/api/v1/bookings/active", headers=admin_auth_headers)

        assert r.status_code == 200
        guest_names = [b["guest_name"] for b in r.json()]
        assert "Huésped Activo" in guest_names


# ---------------------------------------------------------------------------
# Búsqueda global (huésped, nº de reserva o ID) — coincidencia parcial
# ---------------------------------------------------------------------------


class TestGlobalSearchFlow:
    def test_search_finds_guest_in_any_month(self, e2e_client, admin_auth_headers):
        # Reserva lejana (diciembre) y otra cercana, para comprobar que la
        # búsqueda no se limita al periodo visible del calendario.
        e2e_client.post(
            "/api/v1/bookings/",
            json={
                **_BASE_PAYLOAD,
                "apartment_id": "DIC",
                "guest_name": "Huésped Diciembre",
                "check_in": "2026-12-10",
                "check_out": "2026-12-15",
                "nights": 5,
            },
            headers=admin_auth_headers,
        )
        e2e_client.post(
            "/api/v1/bookings/",
            json={**_BASE_PAYLOAD, "apartment_id": "JUN", "guest_name": "Otro Huésped"},
            headers=admin_auth_headers,
        )

        r = e2e_client.get("/api/v1/bookings/?search=diciembre", headers=admin_auth_headers)

        assert r.status_code == 200
        apartment_ids = [b["apartment_id"] for b in r.json()]
        assert apartment_ids == ["DIC"]

    def test_search_matches_record_id_substring(self, e2e_client, admin_auth_headers):
        created_ids = []
        for i in range(15):
            payload = {
                **_BASE_PAYLOAD,
                "apartment_id": f"RID-{i}",
                "check_in": (date(2026, 8, 1) + timedelta(days=i)).isoformat(),
                "check_out": (date(2026, 8, 3) + timedelta(days=i)).isoformat(),
            }
            r = e2e_client.post("/api/v1/bookings/", json=payload, headers=admin_auth_headers)
            assert r.status_code == 201
            created_ids.append(r.json()["record_id"])

        digit = str(created_ids[0])[0]

        r = e2e_client.get(
            f"/api/v1/bookings/?search={digit}&limit=50",
            headers=admin_auth_headers,
        )

        assert r.status_code == 200
        returned = sorted(b["record_id"] for b in r.json())
        expected = sorted(rid for rid in created_ids if digit in str(rid))
        assert returned == expected
        assert len(returned) > 1


# ---------------------------------------------------------------------------
# Flujo de calendario
# ---------------------------------------------------------------------------


class TestCalendarFlow:
    def test_confirmed_booking_appears_in_calendar_events(self, e2e_client, admin_auth_headers):
        payload = {**_BASE_PAYLOAD, "apartment_id": "CAL-E2E", "status": "Confirmed"}
        e2e_client.post("/api/v1/bookings/", json=payload, headers=admin_auth_headers)

        r = e2e_client.get(
            "/api/v1/bookings/calendar-events?start_date=2026-07-01&days=60",
            headers=admin_auth_headers,
        )

        assert r.status_code == 200
        apartment_ids = [ev["extendedProps"]["apartment_id"] for ev in r.json()]
        assert "CAL-E2E" in apartment_ids

    def test_recently_cancelled_booking_excluded_from_calendar(
        self, e2e_client, admin_auth_headers
    ):
        today = date.today()
        cancelled_payload = {
            "apartment_id": "CANCELLED-E2E",
            "guest_name": "Cancelado",
            "check_in": (today + timedelta(days=1)).isoformat(),
            "check_out": (today + timedelta(days=4)).isoformat(),
            "nights": 3,
            "status": "Cancelled",
        }
        e2e_client.post(
            "/api/v1/bookings/",
            json=cancelled_payload,
            headers=admin_auth_headers,
        )

        r = e2e_client.get(
            f"/api/v1/bookings/calendar-events?start_date={today.isoformat()}&days=30",
            headers=admin_auth_headers,
        )

        assert r.status_code == 200
        apartment_ids = [ev["extendedProps"]["apartment_id"] for ev in r.json()]
        assert "CANCELLED-E2E" not in apartment_ids


# ---------------------------------------------------------------------------
# Bonificación eléctrica end-to-end
# ---------------------------------------------------------------------------


class TestElectricAllowanceFlow:
    def test_electric_allowance_calculated_when_apartment_id_in_electric_setting(
        self, e2e_client, admin_auth_headers, monkeypatch
    ):
        from config import settings

        monkeypatch.setattr(settings, "ELECTRIC", "ELEC-E2E-001")

        payload = {
            "apartment_id": "ELEC-E2E-001",
            "guest_name": "Huésped Eléctrico",
            "check_in": "2026-09-01",
            "check_out": "2026-09-04",
            "nights": 3,
        }

        r = e2e_client.post(
            "/api/v1/bookings/",
            json=payload,
            headers=admin_auth_headers,
        )

        assert r.status_code == 201
        data = r.json()
        assert data["electric_allowance"] == 3 * 4.0
