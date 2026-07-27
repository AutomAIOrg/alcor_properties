"""
Integration tests — SQLAlchemyBillRepository contra SQLite en memoria.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from domain.exceptions import BillAlreadyExistsError, BillNotFoundError
from infrastructure.models.bill import BillORM
from infrastructure.models.booking import BookingORM
from infrastructure.repositories.sqlalchemy_bill_repository import SQLAlchemyBillRepository
from tests.helpers import make_bill

pytestmark = pytest.mark.integration


def _insert_booking(session, **overrides) -> BookingORM:
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


def _insert_bill(session, **overrides) -> BillORM:
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


class TestCreate:
    def test_persists_bill_and_assigns_bill_id(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        bill = make_bill(bill_id=None, record_id=booking.record_id)

        result = SQLAlchemyBillRepository(sqlite_session).create(bill)

        assert result.bill_id is not None
        assert result.record_id == booking.record_id
        assert result.state == "Creada"

    def test_persists_created_at(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        bill = make_bill(bill_id=None, record_id=booking.record_id, created_at=date(2026, 6, 24))

        result = SQLAlchemyBillRepository(sqlite_session).create(bill)

        assert result.created_at == date(2026, 6, 24)
        assert SQLAlchemyBillRepository(sqlite_session).get_by_id(
            result.bill_id
        ).created_at == date(2026, 6, 24)

    def test_duplicate_record_id_raises_bill_already_exists(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        repo = SQLAlchemyBillRepository(sqlite_session)
        repo.create(make_bill(bill_id=None, record_id=booking.record_id))

        with pytest.raises(BillAlreadyExistsError):
            repo.create(make_bill(bill_id=None, record_id=booking.record_id))


class TestGetById:
    def test_returns_entity_for_existing_bill(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        orm = _insert_bill(sqlite_session, record_id=booking.record_id)

        result = SQLAlchemyBillRepository(sqlite_session).get_by_id(orm.bill_id)

        assert result.bill_id == orm.bill_id
        assert result.apartment_id == "TEST-001"

    def test_raises_bill_not_found_for_missing_id(self, sqlite_session):
        with pytest.raises(BillNotFoundError):
            SQLAlchemyBillRepository(sqlite_session).get_by_id(9999)


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

    def test_persists_payment_confirmations(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        orm = _insert_bill(sqlite_session, record_id=booking.record_id, state="Creada")
        repo = SQLAlchemyBillRepository(sqlite_session)
        existing = repo.get_by_id(orm.bill_id)

        repo.update(
            existing.model_copy(
                update={
                    "paid_confirmed_by_admin": datetime(2026, 5, 19, 10, 45),
                    "paid_confirmed_by_admin_name": "Admin User",
                    "paid_confirmed_by_cleaner": datetime(2026, 5, 20, 16, 5),
                    "paid_confirmed_by_cleaner_name": "Limpiadora Test",
                }
            )
        )

        reloaded = repo.get_by_id(orm.bill_id)
        assert reloaded.paid_confirmed_by_admin == datetime(2026, 5, 19, 10, 45)
        assert reloaded.paid_confirmed_by_admin_name == "Admin User"
        assert reloaded.paid_confirmed_by_cleaner == datetime(2026, 5, 20, 16, 5)
        assert reloaded.paid_confirmed_by_cleaner_name == "Limpiadora Test"

    def test_persists_cancellation_note(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        orm = _insert_bill(sqlite_session, record_id=booking.record_id, state="Creada")
        repo = SQLAlchemyBillRepository(sqlite_session)
        existing = repo.get_by_id(orm.bill_id)

        updated = repo.update(
            existing.model_copy(
                update={"state": "Cancelada", "cancellation_note": "Reserva duplicada"}
            )
        )

        assert updated.state == "Cancelada"
        assert updated.cancellation_note == "Reserva duplicada"
        # Se persiste realmente (recarga desde la BD).
        assert repo.get_by_id(orm.bill_id).cancellation_note == "Reserva duplicada"


class TestList:
    def test_filters_by_apartment_id(self, sqlite_session):
        b1 = _insert_booking(sqlite_session, apartment_id="B1")
        b2 = _insert_booking(sqlite_session, apartment_id="B2")
        _insert_bill(sqlite_session, record_id=b1.record_id, apartment_id="B1")
        _insert_bill(sqlite_session, record_id=b2.record_id, apartment_id="B2")

        results = SQLAlchemyBillRepository(sqlite_session).list(apartment_id="B1")

        assert len(results) == 1
        assert results[0].apartment_id == "B1"


class TestExistsForBooking:
    def test_returns_true_for_active_bill(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        _insert_bill(sqlite_session, record_id=booking.record_id)

        assert SQLAlchemyBillRepository(sqlite_session).exists_for_booking(booking.record_id)

    def test_returns_false_for_cancelled_bill(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        _insert_bill(sqlite_session, record_id=booking.record_id, state="Cancelada")

        assert not SQLAlchemyBillRepository(sqlite_session).exists_for_booking(booking.record_id)

    def test_returns_false_when_no_bill_exists(self, sqlite_session):
        assert not SQLAlchemyBillRepository(sqlite_session).exists_for_booking(9999)


class TestListBilledBookingIds:
    def test_returns_active_bills_only(self, sqlite_session):
        b1 = _insert_booking(sqlite_session, apartment_id="B1")
        b2 = _insert_booking(sqlite_session, apartment_id="B2")
        b3 = _insert_booking(sqlite_session, apartment_id="B3")
        _insert_bill(sqlite_session, record_id=b1.record_id, apartment_id="B1")
        _insert_bill(
            sqlite_session,
            record_id=b2.record_id,
            apartment_id="B2",
            state="Cancelada",
        )
        _insert_bill(
            sqlite_session,
            record_id=b3.record_id,
            apartment_id="B3",
            state="Pagada",
        )

        result = SQLAlchemyBillRepository(sqlite_session).list_billed_booking_ids()

        assert result == {b1.record_id, b3.record_id}


class TestGetBillStatesByBooking:
    def test_returns_state_map_for_all_bills(self, sqlite_session):
        b1 = _insert_booking(sqlite_session, apartment_id="B1")
        b2 = _insert_booking(sqlite_session, apartment_id="B2")
        _insert_bill(sqlite_session, record_id=b1.record_id, apartment_id="B1", state="Creada")
        _insert_bill(
            sqlite_session,
            record_id=b2.record_id,
            apartment_id="B2",
            state="Cancelada",
        )

        result = SQLAlchemyBillRepository(sqlite_session).get_bill_states_by_booking()

        assert result == {b1.record_id: "Creada", b2.record_id: "Cancelada"}


class TestDeleteCancelledForBooking:
    def test_removes_cancelled_bill_for_record(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        orm = _insert_bill(
            sqlite_session,
            record_id=booking.record_id,
            state="Cancelada",
        )
        repo = SQLAlchemyBillRepository(sqlite_session)

        repo.delete_cancelled_for_booking(booking.record_id)

        assert sqlite_session.get(BillORM, orm.bill_id) is None

    def test_no_op_when_no_cancelled_bill_exists(self, sqlite_session):
        booking = _insert_booking(sqlite_session)
        repo = SQLAlchemyBillRepository(sqlite_session)

        repo.delete_cancelled_for_booking(booking.record_id)

        assert not repo.exists_for_booking(booking.record_id)


class TestListWithoutDocuments:
    def test_returns_created_and_paid_bills_missing_documents(self, sqlite_session):
        from datetime import UTC

        from passlib.context import CryptContext

        from domain.bills.bill_document import BillDocument
        from infrastructure.models.user import UserORM
        from infrastructure.repositories.sqlalchemy_bill_document_repository import (
            SQLAlchemyBillDocumentRepository,
        )

        pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
        user = UserORM(
            username="limpiadora",
            password=pwd.hash("pass"),
            name="Limpiadora",
            lastname="Test",
            email="limpiadora@example.com",
            role="limpiadora",
        )
        sqlite_session.add(user)
        sqlite_session.commit()

        orphan_created = _insert_bill(sqlite_session, apartment_id="O1", state="Creada")
        orphan_paid = _insert_bill(sqlite_session, apartment_id="O2", state="Pagada")
        _insert_bill(sqlite_session, apartment_id="O3", state="Cancelada")
        with_doc = _insert_bill(sqlite_session, apartment_id="O4", state="Creada")

        SQLAlchemyBillDocumentRepository(sqlite_session).create(
            BillDocument(
                bill_id=with_doc.bill_id,
                filename="bill.pdf",
                nas_path="/facturas/bill.pdf",
                content_type="application/pdf",
                size_bytes=10,
                uploaded_by=user.id,
                uploaded_at=datetime.now(UTC),
            )
        )

        result = SQLAlchemyBillRepository(sqlite_session).list_without_documents()

        assert {b.bill_id for b in result} == {orphan_created.bill_id, orphan_paid.bill_id}
