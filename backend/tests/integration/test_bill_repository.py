"""
Integration tests — SQLAlchemyBillRepository contra SQLite en memoria.

No se conecta a MySQL. El mismo Base.metadata crea la tabla bills en SQLite.
"""

from datetime import date
from decimal import Decimal

import pytest

from domain.exceptions import BillAlreadyExists, BillNotFound
from infrastructure.models.bill import BillORM
from infrastructure.models.booking import BookingORM
from infrastructure.repositories.sqlalchemy_bill_repository import (
    SQLAlchemyBillRepository,
)
from tests.helpers import make_bill

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helper de inserción directa (bypass de la capa de dominio)
# ---------------------------------------------------------------------------


def _insert_booking(session, **overrides) -> BookingORM:
    """Inserta un BookingORM previo necesario para el FK de bills."""
    defaults = {
        "apartment_id": "TEST-001",
        "guest_name": "Ana García",
        "check_in": date(2026, 6, 1),
        "check_out": date(2026, 6, 5),
        "nights": 4,
        "status": "Confirmed",
    }
    orm = BookingORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


def _insert_bill(session, **overrides) -> BillORM:
    """Inserta un BillORM con valores por defecto aplicando los overrides dados."""
    defaults = {
        "apartment_id": "TEST-001",
        "clean_hours": Decimal("2.00"),
        "cost": Decimal("30.00"),
        "state": "Creada",
    }
    orm = BillORM(**{**defaults, **overrides})
    session.add(orm)
    session.commit()
    session.refresh(orm)
    return orm


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_persists_bill_and_assigns_bill_id(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        bill = make_bill(bill_id=None, record_id=booking.record_id)

        result = SQLAlchemyBillRepository(sqlite_session).create(bill)

        assert result.bill_id is not None
        assert result.record_id == booking.record_id
        assert result.apartment_id == "TEST-001"
        assert result.clean_hours == Decimal("2.00")
        assert result.cost == Decimal("30.00")
        assert result.state == "Creada"

    def test_duplicate_record_id_raises_bill_already_exists(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        first_bill = make_bill(bill_id=None, record_id=booking.record_id)
        SQLAlchemyBillRepository(sqlite_session).create(first_bill)

        duplicate_bill = make_bill(bill_id=None, record_id=booking.record_id)
        with pytest.raises(BillAlreadyExists):
            SQLAlchemyBillRepository(sqlite_session).create(duplicate_bill)

    def test_allows_multiple_bills_with_null_record_id(self, sqlite_session):
        repo = SQLAlchemyBillRepository(sqlite_session)
        bill1 = make_bill(bill_id=None, record_id=None)
        bill2 = make_bill(bill_id=None, record_id=None)

        result1 = repo.create(bill1)
        result2 = repo.create(bill2)

        assert result1.bill_id != result2.bill_id


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------


class TestGetById:
    def test_returns_entity_for_existing_bill(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        orm = _insert_bill(sqlite_session, record_id=booking.record_id)

        result = SQLAlchemyBillRepository(sqlite_session).get_by_id(orm.bill_id)

        assert result.bill_id == orm.bill_id
        assert result.apartment_id == "TEST-001"

    def test_raises_bill_not_found_for_missing_id(self, sqlite_session):
        with pytest.raises(BillNotFound):
            SQLAlchemyBillRepository(sqlite_session).get_by_id(9999)


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestUpdate:
    def test_persists_state_and_payment_date(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        orm = _insert_bill(sqlite_session, record_id=booking.record_id, state="Creada")
        repo = SQLAlchemyBillRepository(sqlite_session)
        existing = repo.get_by_id(orm.bill_id)

        updated = repo.update(
            existing.model_copy(update={"state": "Pagada", "paid_at": date(2026, 5, 20)})
        )

        assert updated.state == "Pagada"
        assert updated.paid_at == date(2026, 5, 20)
        assert repo.get_by_id(orm.bill_id).paid_at == date(2026, 5, 20)

    def test_raises_bill_not_found_for_missing_bill(self, sqlite_session):
        bill = make_bill(bill_id=9999)
        with pytest.raises(BillNotFound):
            SQLAlchemyBillRepository(sqlite_session).update(bill)


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestList:
    def test_returns_all_bills_without_filters(self, sqlite_session):
        b1 = _insert_booking(sqlite_session, apartment_id="B1")
        b2 = _insert_booking(sqlite_session, apartment_id="B2")
        _insert_bill(sqlite_session, record_id=b1.record_id, apartment_id="B1")
        _insert_bill(sqlite_session, record_id=b2.record_id, apartment_id="B2")

        results = SQLAlchemyBillRepository(sqlite_session).list()

        assert len(results) == 2

    def test_filters_by_record_id(self, sqlite_session):
        b1 = _insert_booking(sqlite_session, apartment_id="B1")
        b2 = _insert_booking(sqlite_session, apartment_id="B2")
        _insert_bill(sqlite_session, record_id=b1.record_id, apartment_id="B1")
        _insert_bill(sqlite_session, record_id=b2.record_id, apartment_id="B2")

        results = SQLAlchemyBillRepository(sqlite_session).list(record_id=b1.record_id)

        assert len(results) == 1
        assert results[0].record_id == b1.record_id

    def test_returns_empty_list_when_no_bills_exist(self, sqlite_session):
        results = SQLAlchemyBillRepository(sqlite_session).list()

        assert results == []


# ---------------------------------------------------------------------------
# exists_for_booking
# ---------------------------------------------------------------------------


class TestExistsForBooking:
    def test_returns_true_when_bill_exists(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        _insert_bill(sqlite_session, record_id=booking.record_id)

        result = SQLAlchemyBillRepository(sqlite_session).exists_for_booking(booking.record_id)

        assert result is True

    def test_returns_false_when_no_bill_exists(self, sqlite_session):
        result = SQLAlchemyBillRepository(sqlite_session).exists_for_booking(9999)

        assert result is False


# ---------------------------------------------------------------------------
# list_billed_booking_ids
# ---------------------------------------------------------------------------


class TestListBilledBookingIds:
    def test_returns_set_of_billed_record_ids(self, sqlite_session):
        b1 = _insert_booking(sqlite_session, apartment_id="B1")
        b2 = _insert_booking(sqlite_session, apartment_id="B2")
        _insert_bill(sqlite_session, record_id=b1.record_id, apartment_id="B1")
        _insert_bill(sqlite_session, record_id=b2.record_id, apartment_id="B2")

        result = SQLAlchemyBillRepository(sqlite_session).list_billed_booking_ids()

        assert result == {b1.record_id, b2.record_id}

    def test_excludes_null_record_ids(self, sqlite_session):
        _insert_bill(sqlite_session, record_id=None)

        result = SQLAlchemyBillRepository(sqlite_session).list_billed_booking_ids()

        assert result == set()

    def test_returns_empty_set_when_no_bills_exist(self, sqlite_session):
        result = SQLAlchemyBillRepository(sqlite_session).list_billed_booking_ids()

        assert result == set()


# ---------------------------------------------------------------------------
# Conversión ORM ↔ Entity
# ---------------------------------------------------------------------------


class TestConversion:
    def test_round_trip_preserves_all_fields(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        bill = make_bill(
            bill_id=None,
            record_id=booking.record_id,
            cleaning_date=date(2026, 5, 25),
            clean_hours=Decimal("1.50"),
            cost=Decimal("22.50"),
        )

        repo = SQLAlchemyBillRepository(sqlite_session)
        created = repo.create(bill)
        fetched = repo.get_by_id(created.bill_id)

        assert fetched.record_id == booking.record_id
        assert fetched.apartment_id == "TEST-001"
        assert fetched.cleaning_date == date(2026, 5, 25)
        assert fetched.clean_hours == Decimal("1.50")
        assert fetched.cost == Decimal("22.50")
        assert fetched.state == "Creada"
