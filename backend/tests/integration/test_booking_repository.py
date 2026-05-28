"""
Integration tests — SQLAlchemyBookingRepository contra SQLite en memoria.

No se conecta a MySQL. El mismo Base.metadata crea la tabla bookings en SQLite.
"""

from datetime import date

import pytest

from domain.exceptions import BookingNotFound
from infrastructure.models.booking import BookingORM
from infrastructure.repositories.sqlalchemy_booking_repository import (
    SQLAlchemyBookingRepository,
)
from tests.helpers import make_booking

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper de inserción directa (bypass de la capa de dominio)
# ---------------------------------------------------------------------------


def _insert_orm(session, **overrides) -> BookingORM:
    """Inserta un BookingORM con valores por defecto aplicando los overrides dados."""
    defaults = {
        "booking_id": "TEST-001",
        "guest_name": "Ana García",
        "check_in": date(2026, 6, 1),
        "check_out": date(2026, 6, 5),
        "nights": 4,
        "status": "Confirmed",
        "persons": 2,
        "adults": 2,
        "children": 0,
    }
    orm = BookingORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetById:
    def test_returns_entity_for_existing_record(self, sqlite_session):
        orm = _insert_orm(sqlite_session)
        result = SQLAlchemyBookingRepository(sqlite_session).get_by_id(orm.record_id)

        assert result.record_id == orm.record_id
        assert result.booking_id == "TEST-001"

    def test_raises_booking_not_found_for_missing_id(self, sqlite_session):
        with pytest.raises(BookingNotFound):
            SQLAlchemyBookingRepository(sqlite_session).get_by_id(9999)

    def test_fallback_values_applied_when_nullable_numeric_fields_are_null(self, sqlite_session):
        orm = _insert_orm(sqlite_session, persons=None, nights=None)
        result = SQLAlchemyBookingRepository(sqlite_session).get_by_id(orm.record_id)

        assert result.guest_name == "Ana García"
        assert result.persons == 1
        assert result.nights == (orm.check_out - orm.check_in).days


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestList:
    def test_returns_all_bookings_without_filters(self, sqlite_session):
        _insert_orm(sqlite_session, booking_id="B1")
        _insert_orm(sqlite_session, booking_id="B2")

        results = SQLAlchemyBookingRepository(sqlite_session).list()

        assert len(results) == 2

    def test_date_range_filter_returns_overlapping_bookings_only(self, sqlite_session):
        _insert_orm(
            sqlite_session,
            booking_id="OVERLAPS",
            check_in=date(2026, 5, 28),
            check_out=date(2026, 6, 3),
            nights=6,
        )
        _insert_orm(
            sqlite_session,
            booking_id="OUTSIDE",
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 5),
            nights=4,
        )

        results = SQLAlchemyBookingRepository(sqlite_session).list(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 30)
        )

        booking_ids = [r.booking_id for r in results]
        assert "OVERLAPS" in booking_ids
        assert "OUTSIDE" not in booking_ids

    def test_limit_restricts_result_count(self, sqlite_session):
        for i in range(5):
            _insert_orm(sqlite_session, booking_id=f"B{i}")

        results = SQLAlchemyBookingRepository(sqlite_session).list(limit=3)

        assert len(results) == 3


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_persists_booking_and_assigns_record_id(self, sqlite_session):
        booking = make_booking()
        result = SQLAlchemyBookingRepository(sqlite_session).create(booking)

        assert result.record_id is not None
        assert result.booking_id == "TEST-001"


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_updates_fields_in_database(self, sqlite_session):
        """
        Este test fallará con AttributeError hasta que se corrija el bug
        'booking.personers' → 'booking.persons' en sqlalchemy_booking_repository.py.
        """
        repo = SQLAlchemyBookingRepository(sqlite_session)
        orm = _insert_orm(sqlite_session, guest_name="Ana García")
        existing = repo.get_by_id(orm.record_id)
        updated = existing.model_copy(update={"guest_name": "Carlos López"})

        result = repo.update(updated)

        assert result.guest_name == "Carlos López"

    def test_raises_booking_not_found_for_missing_record(self, sqlite_session):
        booking = make_booking(record_id=9999)
        with pytest.raises(BookingNotFound):
            SQLAlchemyBookingRepository(sqlite_session).update(booking)


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_removes_booking_from_database(self, sqlite_session):
        repo = SQLAlchemyBookingRepository(sqlite_session)
        orm = _insert_orm(sqlite_session)

        repo.delete(orm.record_id)

        with pytest.raises(BookingNotFound):
            repo.get_by_id(orm.record_id)

    def test_raises_booking_not_found_for_missing_record(self, sqlite_session):
        with pytest.raises(BookingNotFound):
            SQLAlchemyBookingRepository(sqlite_session).delete(9999)
