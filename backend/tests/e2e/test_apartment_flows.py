"""
End-to-end tests — flujos completos de apartamentos.

Stack: TestClient -> Use Cases reales -> SQLAlchemyApartmentRepository -> SQLite.
"""

import pytest

from infrastructure.models.apartment import ApartmentORM

pytestmark = pytest.mark.e2e


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