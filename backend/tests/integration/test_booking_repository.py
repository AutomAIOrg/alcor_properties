"""
Integration tests — SQLAlchemyBookingRepository contra SQLite en memoria.

No se conecta a MySQL. El mismo Base.metadata crea la tabla bookings en SQLite.
"""

from datetime import date, time

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
        "apartment_id": "TEST-001",
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
        assert result.apartment_id == "TEST-001"

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
# search_bookings
# ---------------------------------------------------------------------------


class TestSearchBookings:
    def test_returns_all_bookings_without_filters(self, sqlite_session):
        _insert_orm(sqlite_session, apartment_id="B1")
        _insert_orm(sqlite_session, apartment_id="B2")

        results = SQLAlchemyBookingRepository(sqlite_session).search_bookings()

        assert len(results) == 2

    def test_date_range_filter_returns_overlapping_bookings_only(self, sqlite_session):
        _insert_orm(
            sqlite_session,
            apartment_id="OVERLAPS",
            check_in=date(2026, 5, 28),
            check_out=date(2026, 6, 3),
            nights=6,
        )
        _insert_orm(
            sqlite_session,
            apartment_id="OUTSIDE",
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 5),
            nights=4,
        )

        results = SQLAlchemyBookingRepository(sqlite_session).search_bookings(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 30)
        )

        apartment_ids = [r.apartment_id for r in results]
        assert "OVERLAPS" in apartment_ids
        assert "OUTSIDE" not in apartment_ids

    def test_date_range_filter_uses_exclusive_check_out_boundary(self, sqlite_session):
        _insert_orm(
            sqlite_session,
            apartment_id="ENDS_AT_START",
            check_in=date(2026, 5, 28),
            check_out=date(2026, 6, 1),
            nights=4,
        )
        _insert_orm(
            sqlite_session,
            apartment_id="STARTS_AT_END",
            check_in=date(2026, 6, 30),
            check_out=date(2026, 7, 2),
            nights=2,
        )
        _insert_orm(
            sqlite_session,
            apartment_id="OVERLAPS",
            check_in=date(2026, 6, 29),
            check_out=date(2026, 7, 2),
            nights=3,
        )

        results = SQLAlchemyBookingRepository(sqlite_session).search_bookings(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 30)
        )

        apartment_ids = [r.apartment_id for r in results]
        assert apartment_ids == ["OVERLAPS"]

    def test_start_date_only_returns_bookings_with_checkin_from_start(self, sqlite_session):
        _insert_orm(
            sqlite_session,
            apartment_id="CHECKIN_BEFORE",
            check_in=date(2026, 5, 20),
            check_out=date(2026, 6, 3),
            nights=12,
        )
        _insert_orm(
            sqlite_session,
            apartment_id="CHECKIN_AT_START",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 3),
            nights=2,
        )
        _insert_orm(
            sqlite_session,
            apartment_id="CHECKIN_AFTER",
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 5),
            nights=4,
        )

        results = SQLAlchemyBookingRepository(sqlite_session).search_bookings(
            start_date=date(2026, 6, 1)
        )

        apartment_ids = [r.apartment_id for r in results]
        assert apartment_ids == ["CHECKIN_AT_START", "CHECKIN_AFTER"]

    def test_end_date_only_returns_bookings_with_checkin_until_end(self, sqlite_session):
        _insert_orm(
            sqlite_session,
            apartment_id="CHECKIN_BEFORE_END",
            check_in=date(2026, 5, 28),
            check_out=date(2026, 6, 3),
            nights=6,
        )
        _insert_orm(
            sqlite_session,
            apartment_id="CHECKIN_AT_END",
            check_in=date(2026, 6, 30),
            check_out=date(2026, 7, 2),
            nights=2,
        )
        _insert_orm(
            sqlite_session,
            apartment_id="CHECKIN_AFTER_END",
            check_in=date(2026, 7, 1),
            check_out=date(2026, 7, 5),
            nights=4,
        )

        results = SQLAlchemyBookingRepository(sqlite_session).search_bookings(
            end_date=date(2026, 6, 30)
        )

        apartment_ids = [r.apartment_id for r in results]
        assert apartment_ids == ["CHECKIN_BEFORE_END", "CHECKIN_AT_END"]

    def test_limit_restricts_result_count(self, sqlite_session):
        for i in range(5):
            _insert_orm(sqlite_session, apartment_id=f"B{i}")

        results = SQLAlchemyBookingRepository(sqlite_session).search_bookings(limit=3)

        assert len(results) == 3

    def test_search_matches_by_record_id_substring(self, sqlite_session):
        repo = SQLAlchemyBookingRepository(sqlite_session)
        orms = [_insert_orm(sqlite_session) for _ in range(12)]
        record_ids = [o.record_id for o in orms]
        digit = str(record_ids[0])[0]  # primer dígito de un ID existente

        results = repo.search_bookings(search=digit)

        returned = sorted(r.record_id for r in results)
        expected = sorted(rid for rid in record_ids if digit in str(rid))
        assert returned == expected
        assert returned  # al menos una coincidencia

    def test_search_matches_by_guest_name(self, sqlite_session):
        repo = SQLAlchemyBookingRepository(sqlite_session)
        target = _insert_orm(sqlite_session, apartment_id="MATCH", guest_name="María López")
        _insert_orm(sqlite_session, apartment_id="NOPE", guest_name="Pedro Ruiz")

        results = repo.search_bookings(search="lópez")  # case-insensitive

        apartment_ids = [r.apartment_id for r in results]
        assert apartment_ids == ["MATCH"]
        assert results[0].record_id == target.record_id

    def test_search_matches_by_booking_number(self, sqlite_session):
        repo = SQLAlchemyBookingRepository(sqlite_session)
        _insert_orm(sqlite_session, apartment_id="MATCH", booking_number="BK-2026-777")
        _insert_orm(sqlite_session, apartment_id="NOPE", booking_number="BK-2026-123")

        results = repo.search_bookings(search="777")

        apartment_ids = [r.apartment_id for r in results]
        assert "MATCH" in apartment_ids

    def test_blank_search_is_ignored(self, sqlite_session):
        repo = SQLAlchemyBookingRepository(sqlite_session)
        _insert_orm(sqlite_session, apartment_id="B1")
        _insert_orm(sqlite_session, apartment_id="B2")

        results = repo.search_bookings(search="   ")

        assert len(results) == 2


# ---------------------------------------------------------------------------
# find_overlapping_active
# ---------------------------------------------------------------------------


class TestFindOverlappingActive:
    def test_returns_true_when_active_booking_overlaps(self, sqlite_session):
        _insert_orm(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            nights=4,
        )

        result = SQLAlchemyBookingRepository(sqlite_session).find_overlapping_active(
            apartment_id="R180",
            check_in=date(2026, 6, 4),
            check_out=date(2026, 6, 8),
        )

        assert result is True

    def test_returns_false_for_back_to_back_bookings(self, sqlite_session):
        _insert_orm(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            nights=4,
        )

        result = SQLAlchemyBookingRepository(sqlite_session).find_overlapping_active(
            apartment_id="R180",
            check_in=date(2026, 6, 5),
            check_out=date(2026, 6, 8),
        )

        assert result is False

    def test_returns_false_for_cancelled_booking(self, sqlite_session):
        _insert_orm(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            nights=4,
            status="Cancelled",
        )

        result = SQLAlchemyBookingRepository(sqlite_session).find_overlapping_active(
            apartment_id="R180",
            check_in=date(2026, 6, 2),
            check_out=date(2026, 6, 4),
        )

        assert result is False

    def test_can_exclude_current_booking_from_overlap_search(self, sqlite_session):
        orm = _insert_orm(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            nights=4,
        )

        result = SQLAlchemyBookingRepository(sqlite_session).find_overlapping_active(
            apartment_id="R180",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            exclude_record_id=orm.record_id,
        )

        assert result is False

    def test_exclude_current_booking_still_detects_other_overlaps(self, sqlite_session):
        current = _insert_orm(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            nights=4,
        )
        _insert_orm(
            sqlite_session,
            apartment_id="R180",
            check_in=date(2026, 6, 4),
            check_out=date(2026, 6, 8),
            nights=4,
        )

        result = SQLAlchemyBookingRepository(sqlite_session).find_overlapping_active(
            apartment_id="R180",
            check_in=date(2026, 6, 3),
            check_out=date(2026, 6, 6),
            exclude_record_id=current.record_id,
        )

        assert result is True


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_persists_booking_and_assigns_record_id(self, sqlite_session):
        booking = make_booking()
        result = SQLAlchemyBookingRepository(sqlite_session).create(booking)

        assert result.record_id is not None
        assert result.apartment_id == "TEST-001"


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

    def test_persists_notes_cleaning_separately_from_notes(self, sqlite_session):
        repo = SQLAlchemyBookingRepository(sqlite_session)
        orm = _insert_orm(
            sqlite_session, notes="Nota reserva", notes_cleaning="Instrucciones limpieza"
        )
        existing = repo.get_by_id(orm.record_id)
        updated = existing.model_copy(update={"notes_cleaning": "Llaves en conserjería"})

        result = repo.update(updated)

        assert result.notes == "Nota reserva"
        assert result.notes_cleaning == "Llaves en conserjería"

    def test_persists_agreed_check_times(self, sqlite_session):
        repo = SQLAlchemyBookingRepository(sqlite_session)
        orm = _insert_orm(sqlite_session)
        existing = repo.get_by_id(orm.record_id)
        assert existing.check_in_time is None
        assert existing.check_out_time is None

        updated = existing.model_copy(
            update={"check_in_time": time(18, 0), "check_out_time": time(13, 30)}
        )
        result = repo.update(updated)

        assert result.check_in_time == time(18, 0)
        assert result.check_out_time == time(13, 30)
        assert repo.get_by_id(orm.record_id).check_out_time == time(13, 30)

    def test_clears_agreed_check_times_back_to_standard(self, sqlite_session):
        repo = SQLAlchemyBookingRepository(sqlite_session)
        orm = _insert_orm(sqlite_session, check_in_time=time(18, 0), check_out_time=time(13, 30))
        existing = repo.get_by_id(orm.record_id)

        updated = existing.model_copy(update={"check_in_time": None, "check_out_time": None})
        result = repo.update(updated)

        assert result.check_in_time is None
        assert result.check_out_time is None
        assert result.effective_check_out_time() == time(11, 0)

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
