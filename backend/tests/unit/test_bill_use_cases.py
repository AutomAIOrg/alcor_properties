"""
Unit tests — casos de uso de facturas (crear, actualizar estado, listar pendientes).
"""

from datetime import date, datetime, time
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from application.bills.create_bill_use_case import CreateBillData, CreateBillUseCase
from application.bills.list_bills_use_cases import ListPendingBillsUseCase
from application.bills.update_bill_use_case import UpdateBillStateUseCase
from domain.bills.repository import IBillRepository
from domain.bookings.repository import IBookingRepository
from domain.exceptions import (
    BillAlreadyExistsError,
    BillNotFoundError,
    BookingNotFound,
    DomainValidationError,
)
from tests.helpers import make_bill, make_booking

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 6, 24, 12, 0)
_WEEK_START = date(2026, 6, 22)


def _create_use_case(
    bills: MagicMock,
    bookings: MagicMock,
    rate: Decimal = Decimal("15"),
) -> CreateBillUseCase:
    return CreateBillUseCase(bills, bookings, rate)


def _create_data(**overrides) -> CreateBillData:
    defaults = {
        "record_id": 5,
        "cleaning_date": date(2026, 5, 25),
        "start_time": time(10, 0),
        "end_time": time(12, 0),
    }
    return CreateBillData(**{**defaults, **overrides})


# ---------------------------------------------------------------------------
# CreateBillUseCase
# ---------------------------------------------------------------------------


class TestCreateBillUseCase:
    def test_derives_apartment_hours_cost_and_state(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.return_value = make_booking(record_id=5, apartment_id="R180")
        bills = MagicMock(spec=IBillRepository)
        bills.exists_for_booking.return_value = False
        bills.create.side_effect = lambda bill: bill

        result = _create_use_case(bills, bookings).execute(
            _create_data(start_time=time(10, 0), end_time=time(11, 30))
        )

        assert result.apartment_id == "R180"
        assert result.record_id == 5
        assert result.cleaning_date == date(2026, 5, 25)
        assert result.clean_hours == Decimal("1.50")
        assert result.cost == Decimal("22.50")
        assert result.state == "Creada"
        bills.create.assert_called_once()

    def test_uses_payload_hourly_rate_when_provided(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.return_value = make_booking(record_id=5)
        bills = MagicMock(spec=IBillRepository)
        bills.exists_for_booking.return_value = False
        bills.create.side_effect = lambda bill: bill

        result = _create_use_case(bills, bookings, rate=Decimal("10")).execute(
            _create_data(hourly_rate=Decimal("20"))
        )

        assert result.hourly_rate == Decimal("20.00")
        assert result.cost == Decimal("40.00")

    def test_uses_injected_rate_when_payload_rate_is_none(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.return_value = make_booking(record_id=5)
        bills = MagicMock(spec=IBillRepository)
        bills.exists_for_booking.return_value = False
        bills.create.side_effect = lambda bill: bill

        result = _create_use_case(bills, bookings, rate=Decimal("12.50")).execute(_create_data())

        assert result.hourly_rate == Decimal("12.50")
        assert result.cost == Decimal("25.00")

    def test_raises_when_bill_already_exists_for_booking(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.return_value = make_booking(record_id=5)
        bills = MagicMock(spec=IBillRepository)
        bills.exists_for_booking.return_value = True

        with pytest.raises(BillAlreadyExistsError):
            _create_use_case(bills, bookings).execute(_create_data())

        bills.create.assert_not_called()

    def test_raises_when_booking_not_found(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.side_effect = BookingNotFound(5)
        bills = MagicMock(spec=IBillRepository)

        with pytest.raises(BookingNotFound):
            _create_use_case(bills, bookings).execute(_create_data())

        bills.exists_for_booking.assert_not_called()
        bills.create.assert_not_called()

    def test_raises_when_booking_is_cancelled(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.return_value = make_booking(record_id=5, status="cancelled")
        bills = MagicMock(spec=IBillRepository)

        with pytest.raises(DomainValidationError, match="cancelada"):
            _create_use_case(bills, bookings).execute(_create_data())

        bills.exists_for_booking.assert_not_called()
        bills.create.assert_not_called()

    def test_raises_when_checkout_not_yet_occurred(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.return_value = make_booking(
            record_id=5,
            check_in=date(2026, 12, 1),
            check_out=date(2026, 12, 10),
        )
        bills = MagicMock(spec=IBillRepository)

        with pytest.raises(DomainValidationError, match="check-out"):
            _create_use_case(bills, bookings).execute(_create_data())

        bills.exists_for_booking.assert_not_called()
        bills.create.assert_not_called()

    def test_raises_when_end_time_not_after_start_time(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.return_value = make_booking(record_id=5)
        bills = MagicMock(spec=IBillRepository)
        bills.exists_for_booking.return_value = False

        with pytest.raises(DomainValidationError):
            _create_use_case(bills, bookings).execute(
                _create_data(start_time=time(12, 0), end_time=time(10, 0))
            )

        bills.create.assert_not_called()

    def test_deletes_cancelled_bill_before_creating_new_one(self):
        bookings = MagicMock(spec=IBookingRepository)
        bookings.get_by_id.return_value = make_booking(record_id=5)
        bills = MagicMock(spec=IBillRepository)
        bills.exists_for_booking.return_value = False
        bills.create.side_effect = lambda bill: bill

        _create_use_case(bills, bookings).execute(_create_data())

        bills.delete_cancelled_for_booking.assert_called_once_with(5)


# ---------------------------------------------------------------------------
# UpdateBillStateUseCase
# ---------------------------------------------------------------------------


def _update_use_case(bills: MagicMock) -> UpdateBillStateUseCase:
    return UpdateBillStateUseCase(bills)


def _bills_with(bill) -> MagicMock:
    bills = MagicMock(spec=IBillRepository)
    bills.get_by_id.return_value = bill
    bills.update.side_effect = lambda updated: updated
    return bills


class TestUpdateBillStateUseCase:
    def test_created_to_paid_sets_payment_date_today(self):
        bills = _bills_with(make_bill(bill_id=1, state="Creada"))
        frozen_today = date(2026, 6, 15)

        with patch("application.bills.update_bill_use_case.date") as mock_date:
            mock_date.today.return_value = frozen_today
            result = _update_use_case(bills).execute(1, "Pagada")

        assert result.state == "Pagada"
        assert result.paid_at == frozen_today

    def test_created_to_paid_uses_explicit_payment_date(self):
        bills = _bills_with(make_bill(bill_id=1, state="Creada"))

        result = _update_use_case(bills).execute(1, "Pagada", paid_at=date(2026, 5, 20))

        assert result.paid_at == date(2026, 5, 20)

    def test_paid_to_created_clears_payment_date(self):
        bills = _bills_with(make_bill(bill_id=1, state="Pagada", paid_at=date(2026, 5, 20)))

        result = _update_use_case(bills).execute(1, "Creada")

        assert result.state == "Creada"
        assert result.paid_at is None

    def test_created_to_cancelled_stores_note(self):
        bills = _bills_with(make_bill(bill_id=1, state="Creada"))

        result = _update_use_case(bills).execute(
            1, "Cancelada", cancellation_note="Reserva duplicada"
        )

        assert result.state == "Cancelada"
        assert result.cancellation_note == "Reserva duplicada"

    def test_cancelled_without_note_stores_none(self):
        bills = _bills_with(make_bill(bill_id=1, state="Creada"))

        result = _update_use_case(bills).execute(1, "Cancelada", cancellation_note="   ")

        assert result.state == "Cancelada"
        assert result.cancellation_note is None

    def test_reactivating_cancelled_clears_note(self):
        bills = _bills_with(
            make_bill(bill_id=1, state="Cancelada", cancellation_note="Motivo previo")
        )

        result = _update_use_case(bills).execute(1, "Creada")

        assert result.state == "Creada"
        assert result.cancellation_note is None

    def test_note_ignored_when_not_cancelling(self):
        bills = _bills_with(make_bill(bill_id=1, state="Creada"))

        result = _update_use_case(bills).execute(
            1, "Pagada", cancellation_note="No debería guardarse"
        )

        assert result.state == "Pagada"
        assert result.cancellation_note is None

    def test_invalid_transition_raises_validation_error(self):
        bills = _bills_with(make_bill(bill_id=1, state="Pagada"))

        with pytest.raises(DomainValidationError):
            _update_use_case(bills).execute(1, "Cancelada")

        bills.update.assert_not_called()

    def test_missing_bill_raises_not_found(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.side_effect = BillNotFoundError(99)

        with pytest.raises(BillNotFoundError):
            _update_use_case(bills).execute(99, "Pagada")

        bills.update.assert_not_called()


# ---------------------------------------------------------------------------
# ListPendingBillsUseCase
# ---------------------------------------------------------------------------


def _pending_query(
    bookings: list,
    billed_ids: set[int] | None = None,
    bill_states: dict[int, str] | None = None,
) -> ListPendingBillsUseCase:
    booking_repo = MagicMock(spec=IBookingRepository)
    booking_repo.search_bookings.return_value = bookings
    bill_repo = MagicMock(spec=IBillRepository)
    bill_repo.list_billed_booking_ids.return_value = billed_ids or set()
    bill_repo.get_bill_states_by_booking.return_value = bill_states or {}
    return ListPendingBillsUseCase(booking_repo, bill_repo)


class TestListPendingBillsUseCase:
    def test_includes_cleanable_booking_without_bill(self):
        bookings = [
            make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 23))
        ]

        result = _pending_query(bookings).execute(reference_datetime=_NOW)

        assert len(result) == 1
        assert result[0].record_id == 1
        assert result[0].state == "Pendiente"
        assert result[0].bill_id is None

    def test_excludes_already_billed_bookings(self):
        bookings = [
            make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 23))
        ]

        result = _pending_query(bookings, billed_ids={1}).execute(reference_datetime=_NOW)

        assert result == []

    def test_excludes_not_yet_cleanable_checkout(self):
        bookings = [
            make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 24))
        ]

        result = _pending_query(bookings).execute(reference_datetime=datetime(2026, 6, 24, 9, 0))

        assert result == []

    def test_includes_today_checkout_after_default_checkout_time(self):
        bookings = [
            make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 24))
        ]

        result = _pending_query(bookings).execute(reference_datetime=datetime(2026, 6, 24, 11, 30))

        assert len(result) == 1
        assert result[0].record_id == 1

    def test_excludes_future_checkout(self):
        bookings = [
            make_booking(record_id=1, check_in=date(2026, 6, 24), check_out=date(2026, 6, 26))
        ]

        result = _pending_query(bookings).execute(reference_datetime=_NOW)

        assert result == []

    def test_excludes_checkout_before_current_week(self):
        bookings = [
            make_booking(record_id=1, check_in=date(2026, 6, 12), check_out=date(2026, 6, 15))
        ]

        result = _pending_query(bookings).execute(reference_datetime=_NOW)

        assert result == []

    def test_includes_checkout_on_week_start_monday(self):
        bookings = [make_booking(record_id=1, check_in=date(2026, 6, 19), check_out=_WEEK_START)]

        result = _pending_query(bookings).execute(reference_datetime=_NOW)

        assert len(result) == 1
        assert result[0].cleaning_date == _WEEK_START

    def test_pending_with_cancelled_bill_is_flagged(self):
        bookings = [
            make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 23))
        ]

        result = _pending_query(bookings, bill_states={1: "Cancelada"}).execute(
            reference_datetime=_NOW
        )

        assert len(result) == 1
        assert result[0].previously_cancelled is True

    def test_date_to_filters_out_later_checkouts(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="A1",
                check_in=date(2026, 6, 20),
                check_out=date(2026, 6, 22),
            ),
            make_booking(
                record_id=2,
                apartment_id="A2",
                check_in=date(2026, 6, 21),
                check_out=date(2026, 6, 23),
            ),
        ]

        result = _pending_query(bookings).execute(
            reference_datetime=_NOW, date_to=date(2026, 6, 22)
        )

        assert [bill.record_id for bill in result] == [1]

    def test_apartment_filter_keeps_only_matching_apartment(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 20),
                check_out=date(2026, 6, 22),
            ),
            make_booking(
                record_id=2,
                apartment_id="R200",
                check_in=date(2026, 6, 20),
                check_out=date(2026, 6, 23),
            ),
        ]

        result = _pending_query(bookings).execute(apartment_id="R180", reference_datetime=_NOW)

        assert [bill.record_id for bill in result] == [1]
