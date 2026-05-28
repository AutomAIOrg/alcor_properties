"""
Integration tests — funciones del router de búsquedas con SQLite.

Evita TestClient y llama directamente a los endpoints con una Session real.
"""

from datetime import date

import pytest

from api.v1.searches.router import get_booking_search_options, search_bookings
from infrastructure.models.apartment import ApartmentORM
from infrastructure.models.booking import BookingORM

pytestmark = pytest.mark.integration


def _insert_apartment(session, **overrides) -> ApartmentORM:
    defaults = {
        "booking_id": "R180",
        "community": "Alta Entinas",
        "booking_name": "Apartamento familiar",
        "address": "Calle Glaucio 15",
        "bedrooms": 2,
        "bathrooms": 2,
        "parking": "63",
        "total_occupancy": 6,
        "owner_name": "Katarzyna Tokarska",
        "owner_email": "owner@example.com",
        "owner_phone": "+34 600 000 000",
    }
    orm = ApartmentORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


def _insert_booking(session, **overrides) -> BookingORM:
    defaults = {
        "booking_id": "R180",
        "guest_name": "Ana Garcia",
        "check_in": date(2026, 6, 1),
        "check_out": date(2026, 6, 5),
        "nights": 4,
        "status": "Confirmed",
        "persons": 2,
        "adults": 2,
        "children": 0,
        "booking_number": "BK-001",
    }
    orm = BookingORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


class TestSearchBookingsRouter:
    def test_returns_paginated_response_with_serialized_apartment(self, sqlite_session):
        _insert_apartment(
            sqlite_session,
            booking_id="R180",
            community="Alta Entinas",
            booking_name="Apartamento familiar",
            address="Calle Glaucio 15",
            bedrooms=2,
            bathrooms=2,
            parking="63",
            total_occupancy=6,
            owner_name="Katarzyna Tokarska",
            owner_email="owner@example.com",
            owner_phone="+34 600 000 000",
        )
        _insert_booking(sqlite_session, booking_id="R180", guest_name="Ana Garcia")

        response = search_bookings(
            q=None,
            start_date=None,
            end_date=None,
            date_mode="movement",
            booking_ids=None,
            statuses=None,
            sort_by="check_in",
            sort_dir="asc",
            limit=10,
            offset=0,
            db=sqlite_session,
        )

        assert response.total == 1
        assert response.limit == 10
        assert response.offset == 0
        assert response.items[0].booking_id == "R180"
        apartment = response.items[0].apartment
        assert apartment is not None
        assert apartment.booking_id == "R180"
        assert apartment.community == "Alta Entinas"
        assert apartment.booking_name == "Apartamento familiar"
        assert apartment.address == "Calle Glaucio 15"
        assert apartment.bedrooms == 2
        assert apartment.bathrooms == 2
        assert apartment.parking == "63"
        assert apartment.total_occupancy == 6
        assert apartment.owner_name == "Katarzyna Tokarska"
        assert apartment.owner_email == "owner@example.com"
        assert apartment.owner_phone == "+34 600 000 000"

    def test_returns_filter_options(self, sqlite_session):
        _insert_apartment(sqlite_session, booking_id="R221")
        _insert_apartment(sqlite_session, booking_id="R180")
        _insert_booking(sqlite_session, booking_id="R180", status="Confirmed")
        _insert_booking(sqlite_session, booking_id="R999", status="Cancelled")

        response = get_booking_search_options(db=sqlite_session)

        assert response.booking_ids == ["R180", "R221"]
        assert response.statuses == ["Cancelled", "Confirmed"]
