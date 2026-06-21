"""
End-to-end tests — configuración del precio por hora de limpieza.

Verifica que el precio se persiste, se expone y que las nuevas facturas lo usan.
"""

import pytest

pytestmark = pytest.mark.e2e


_BOOKING_PAYLOAD = {
    "apartment_id": "E2E-RATE-001",
    "guest_name": "Huésped Tarifa",
    "check_in": "2026-08-01",
    "check_out": "2026-08-05",
    "nights": 4,
}


class TestCleaningRateSettings:
    def test_get_and_update_rate(self, e2e_client, admin_auth_headers):
        r = e2e_client.get("/api/v1/settings/cleaning-rate", headers=admin_auth_headers)
        assert r.status_code == 200
        assert "cleaning_hourly_rate" in r.json()

        r = e2e_client.put(
            "/api/v1/settings/cleaning-rate",
            json={"cleaning_hourly_rate": 18.5},
            headers=admin_auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["cleaning_hourly_rate"] == 18.5

        r = e2e_client.get("/api/v1/settings/cleaning-rate", headers=admin_auth_headers)
        assert r.json()["cleaning_hourly_rate"] == 18.5

    def test_new_bill_uses_updated_rate(self, e2e_client, admin_auth_headers):
        e2e_client.put(
            "/api/v1/settings/cleaning-rate",
            json={"cleaning_hourly_rate": 20},
            headers=admin_auth_headers,
        )

        r = e2e_client.post("/api/v1/bookings/", json=_BOOKING_PAYLOAD, headers=admin_auth_headers)
        record_id = r.json()["record_id"]

        r = e2e_client.post(
            "/api/v1/bills/",
            json={
                "record_id": record_id,
                "cleaning_date": "2026-08-05",
                "start_time": "10:00",
                "end_time": "12:00",  # 2 horas
            },
            headers=admin_auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["cost"] == 40.0  # 2 h × 20 €

    def test_negative_rate_returns_422(self, e2e_client, admin_auth_headers):
        r = e2e_client.put(
            "/api/v1/settings/cleaning-rate",
            json={"cleaning_hourly_rate": -5},
            headers=admin_auth_headers,
        )
        assert r.status_code == 422

    def test_cleaner_can_read_but_not_update_rate(self, e2e_client, cleaner_auth_headers):
        # La limpiadora puede leer la tarifa (la necesita al generar factura)...
        r = e2e_client.get("/api/v1/settings/cleaning-rate", headers=cleaner_auth_headers)
        assert r.status_code == 200
        assert "cleaning_hourly_rate" in r.json()

        # ...pero no puede modificarla.
        r = e2e_client.put(
            "/api/v1/settings/cleaning-rate",
            json={"cleaning_hourly_rate": 10},
            headers=cleaner_auth_headers,
        )
        assert r.status_code == 403
