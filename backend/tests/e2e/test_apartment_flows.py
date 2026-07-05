"""
End-to-end tests — flujos completos de apartamentos.

Stack: TestClient -> Use Cases reales -> SQLAlchemyApartmentRepository -> SQLite.
"""

from datetime import date, timedelta

import pytest

from infrastructure.models.apartment import ApartmentORM
from infrastructure.models.booking import BookingORM

pytestmark = pytest.mark.e2e

_CREATE_PAYLOAD = {
    "apartment_id": "APT-CRUD-001",
    "community": "Alta Entinas",
    "apartment_description": "Apartamento e2e CRUD",
    "address": "Calle E2E 1",
    "rooms": 2,
    "bathrooms": 1,
    "parking": "P42",
    "total_occupants": 4,
    "owner_name": "Owner E2E",
    "email": "owner-e2e@example.com",
    "phone": "+34 600 111 222",
}

_UPDATE_PAYLOAD = {
    "community": "Comunidad Actualizada",
    "apartment_description": "Apartamento actualizado e2e",
    "address": "Calle E2E 99",
    "rooms": 3,
    "bathrooms": 2,
    "parking": "P99",
    "total_occupants": 6,
    "owner_name": "Owner Actualizado",
    "email": "updated-e2e@example.com",
    "phone": "+34 600 999 888",
}


class TestApartmentSearchFlow:
    def test_admin_can_search_apartments_from_sqlite(
        self,
        sqlite_session,
        e2e_client,
        admin_auth_headers,
    ):
        apartment = ApartmentORM(
            apartment_id="APT-E2E-001",
            community="Alta Entinas",
            apartment_description="Apartamento e2e",
            address="Calle E2E 1",
            rooms=2,
            bathrooms=1,
            parking="P42",
            total_occupants=4,
            owner_name="Owner E2E",
            email="owner-e2e@example.com",
            phone="+34 600 111 222",
        )
        sqlite_session.add(apartment)
        sqlite_session.commit()

        response = e2e_client.get(
            "/api/v1/apartments/search?q=entinas",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["apartment_id"] == "APT-E2E-001"
        assert data[0]["community"] == "Alta Entinas"
        assert data[0]["rooms"] == 2
        assert data[0]["parking"] == "P42"


class TestApartmentAdminCrudFlow:
    def test_admin_can_create_list_update_and_delete_apartment(
        self,
        e2e_client,
        admin_auth_headers,
    ):
        create_response = e2e_client.post(
            "/api/v1/apartments/",
            json=_CREATE_PAYLOAD,
            headers=admin_auth_headers,
        )
        assert create_response.status_code == 200
        assert create_response.json() == {"message": "Apartamento creado correctamente"}

        list_response = e2e_client.get("/api/v1/apartments", headers=admin_auth_headers)
        assert list_response.status_code == 200
        apartment_ids = [item["apartment_id"] for item in list_response.json()]
        assert "APT-CRUD-001" in apartment_ids

        update_response = e2e_client.put(
            "/api/v1/apartments/APT-CRUD-001",
            json=_UPDATE_PAYLOAD,
            headers=admin_auth_headers,
        )
        assert update_response.status_code == 200
        assert update_response.json() == {"message": "Apartamento actualizado correctamente"}

        get_response = e2e_client.get(
            "/api/v1/apartments/APT-CRUD-001",
            headers=admin_auth_headers,
        )
        assert get_response.status_code == 200
        updated = get_response.json()
        assert updated["community"] == "Comunidad Actualizada"
        assert updated["rooms"] == 3
        assert updated["parking"] == "P99"

        delete_response = e2e_client.delete(
            "/api/v1/apartments/APT-CRUD-001",
            headers=admin_auth_headers,
        )
        assert delete_response.status_code == 200
        assert delete_response.json() == {"message": "Apartamento eliminado correctamente"}

        missing_response = e2e_client.get(
            "/api/v1/apartments/APT-CRUD-001",
            headers=admin_auth_headers,
        )
        assert missing_response.status_code == 404


class TestApartmentDeleteWithBookings:
    def test_cannot_delete_apartment_with_future_confirmed_booking(
        self,
        sqlite_session,
        e2e_client,
        admin_auth_headers,
    ):
        sqlite_session.add(
            ApartmentORM(
                apartment_id="APT-BLOCKED",
                community="Test",
                apartment_description="Bloqueado",
                address="Calle 1",
                rooms=2,
                bathrooms=1,
                parking="P1",
                total_occupants=4,
            )
        )
        today = date.today()
        sqlite_session.add(
            BookingORM(
                apartment_id="APT-BLOCKED",
                guest_name="Huésped Futuro",
                check_in=today + timedelta(days=10),
                check_out=today + timedelta(days=15),
                nights=5,
                status="Confirmed",
            )
        )
        sqlite_session.commit()

        response = e2e_client.delete(
            "/api/v1/apartments/APT-BLOCKED",
            headers=admin_auth_headers,
        )

        assert response.status_code == 409
        assert "reservas" in response.json()["detail"].lower()

    def test_can_delete_apartment_with_cancelled_future_booking(
        self,
        sqlite_session,
        e2e_client,
        admin_auth_headers,
    ):
        sqlite_session.add(
            ApartmentORM(
                apartment_id="APT-CANCELLED",
                community="Test",
                apartment_description="Cancelado",
                address="Calle 2",
                rooms=2,
                bathrooms=1,
                parking="P2",
                total_occupants=4,
            )
        )
        today = date.today()
        sqlite_session.add(
            BookingORM(
                apartment_id="APT-CANCELLED",
                guest_name="Huésped Cancelado",
                check_in=today + timedelta(days=10),
                check_out=today + timedelta(days=15),
                nights=5,
                status="Cancelled",
            )
        )
        sqlite_session.commit()

        response = e2e_client.delete(
            "/api/v1/apartments/APT-CANCELLED",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        assert response.json() == {"message": "Apartamento eliminado correctamente"}
