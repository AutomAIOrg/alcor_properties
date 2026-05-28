"""
Integration tests — SQLAlchemySearchRepository contra SQLite en memoria.

Valida filtros de texto, fecha, estado, piso, ordenación, paginación y opciones
sin conectar contra MySQL.
"""

from datetime import date

import pytest

from api.v1.searches.schemas import BookingSearchFilters
from infrastructure.models.apartment import ApartmentORM
from infrastructure.models.booking import BookingORM
from infrastructure.repositories.sqlalchemy_search_repository import SQLAlchemySearchRepository

pytestmark = pytest.mark.integration


def _insert_apartment(session, **overrides) -> ApartmentORM:
    """Inserta un ApartmentORM con valores por defecto aplicando overrides."""
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
    """Inserta un BookingORM con valores por defecto aplicando overrides."""
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
        "email": "ana@example.com",
        "phone": "+34 611 111 111",
    }
    orm = BookingORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


class TestSearchTextAndJoin:
    def test_text_search_matches_booking_fields(self, sqlite_session):
        _insert_booking(sqlite_session, booking_id="R180", guest_name="Ana Garcia")
        _insert_booking(sqlite_session, booking_id="R221", guest_name="Carlos Lopez")

        rows, total = SQLAlchemySearchRepository(sqlite_session).search_bookings(
            BookingSearchFilters(q="garcia")
        )

        assert total == 1
        assert rows[0][0].guest_name == "Ana Garcia"

    def test_text_search_matches_apartment_fields_and_returns_apartment(self, sqlite_session):
        _insert_apartment(sqlite_session, booking_id="R180", community="Alta Entinas")
        _insert_booking(sqlite_session, booking_id="R180", guest_name="Ana Garcia")
        _insert_booking(sqlite_session, booking_id="R221", guest_name="Carlos Lopez")

        rows, total = SQLAlchemySearchRepository(sqlite_session).search_bookings(
            BookingSearchFilters(q="entinas")
        )

        booking, apartment = rows[0]
        assert total == 1
        assert booking.booking_id == "R180"
        assert apartment is not None
        assert apartment.community == "Alta Entinas"


class TestDateModes:
    @pytest.mark.parametrize(
        ("date_mode", "expected_ids"),
        [
            ("movement", {"CHECKIN", "CHECKOUT"}),
            ("check_in", {"CHECKIN"}),
            ("check_out", {"CHECKOUT"}),
            ("stay", {"CHECKIN", "CHECKOUT", "STAY_ONLY"}),
        ],
    )
    def test_date_mode_filters_expected_bookings(self, sqlite_session, date_mode, expected_ids):
        _insert_booking(
            sqlite_session,
            booking_id="CHECKIN",
            check_in=date(2026, 6, 10),
            check_out=date(2026, 6, 20),
            nights=10,
        )
        _insert_booking(
            sqlite_session,
            booking_id="CHECKOUT",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 11),
            nights=10,
        )
        _insert_booking(
            sqlite_session,
            booking_id="STAY_ONLY",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 20),
            nights=19,
        )
        _insert_booking(
            sqlite_session,
            booking_id="OUTSIDE",
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 5),
            nights=4,
        )

        rows, _ = SQLAlchemySearchRepository(sqlite_session).search_bookings(
            BookingSearchFilters(
                start_date=date(2026, 6, 10),
                end_date=date(2026, 6, 12),
                date_mode=date_mode,
            )
        )

        assert {booking.booking_id for booking, _ in rows} == expected_ids

    def test_single_date_filter_uses_same_day_for_start_and_end(self, sqlite_session):
        _insert_booking(
            sqlite_session,
            booking_id="CHECKOUT_TODAY",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 11),
            nights=10,
        )
        _insert_booking(
            sqlite_session,
            booking_id="OUTSIDE",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 12),
            nights=11,
        )

        rows, _ = SQLAlchemySearchRepository(sqlite_session).search_bookings(
            BookingSearchFilters(start_date=date(2026, 6, 11), date_mode="check_out")
        )

        assert [booking.booking_id for booking, _ in rows] == ["CHECKOUT_TODAY"]


class TestSearchFiltersAndOptions:
    def test_filters_by_booking_id_and_status(self, sqlite_session):
        _insert_booking(sqlite_session, booking_id="R180", status="Confirmed")
        _insert_booking(sqlite_session, booking_id="R180", status="Cancelled")
        _insert_booking(sqlite_session, booking_id="R221", status="Confirmed")

        rows, total = SQLAlchemySearchRepository(sqlite_session).search_bookings(
            BookingSearchFilters(booking_ids=["R180"], statuses=["Cancelled"])
        )

        assert total == 1
        assert rows[0][0].booking_id == "R180"
        assert rows[0][0].status == "Cancelled"

    def test_sorting_pagination_and_total(self, sqlite_session):
        _insert_booking(sqlite_session, booking_id="EARLY", check_in=date(2026, 6, 1))
        _insert_booking(sqlite_session, booking_id="MIDDLE", check_in=date(2026, 6, 10))
        _insert_booking(sqlite_session, booking_id="LATE", check_in=date(2026, 6, 20))

        rows, total = SQLAlchemySearchRepository(sqlite_session).search_bookings(
            BookingSearchFilters(sort_by="check_in", sort_dir="desc", limit=1, offset=1)
        )

        assert total == 3
        assert len(rows) == 1
        assert rows[0][0].booking_id == "MIDDLE"

    def test_sorts_by_apartment_field(self, sqlite_session):
        _insert_apartment(sqlite_session, booking_id="R221", community="Zenata")
        _insert_apartment(sqlite_session, booking_id="R180", community="Alta Entinas")
        _insert_booking(sqlite_session, booking_id="R221")
        _insert_booking(sqlite_session, booking_id="R180")

        rows, total = SQLAlchemySearchRepository(sqlite_session).search_bookings(
            BookingSearchFilters(sort_by="community", sort_dir="asc")
        )

        assert total == 2
        assert [booking.booking_id for booking, _ in rows] == ["R180", "R221"]

    def test_get_options_returns_apartments_and_statuses_sorted(self, sqlite_session):
        _insert_apartment(sqlite_session, booking_id="R221")
        _insert_apartment(sqlite_session, booking_id="R180")
        _insert_booking(sqlite_session, booking_id="R180", status="Confirmed")
        _insert_booking(sqlite_session, booking_id="R999", status="Cancelled")

        booking_ids, statuses = SQLAlchemySearchRepository(sqlite_session).get_options()

        assert booking_ids == ["R180", "R221"]
        assert statuses == ["Cancelled", "Confirmed"]
