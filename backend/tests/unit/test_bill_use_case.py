"""
Unit tests — caso de uso de creación de facturas.
"""

from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from application.bills.commands import CreateBillData, CreateBillUseCase
from domain.bills.repository import IBillRepository
from domain.bookings.repository import IBookingRepository
from domain.exceptions import BillAlreadyExists, BookingNotFound, DomainValidationError
from tests.helpers import make_booking

pytestmark = pytest.mark.unit


def _use_case(bills: MagicMock, bookings: MagicMock, rate: Decimal = Decimal("15")):
    return CreateBillUseCase(bills, bookings, rate)


def _data(**overrides) -> CreateBillData:
    defaults = {
        "record_id": 5,
        "cleaning_date": date(2026, 5, 25),
        "start_time": time(10, 0),
        "end_time": time(12, 0),
    }
    return CreateBillData(**{**defaults, **overrides})


def test_derives_apartment_hours_cost_and_state():
    bookings = MagicMock(spec=IBookingRepository)
    bookings.get_by_id.return_value = make_booking(record_id=5, apartment_id="R180")
    bills = MagicMock(spec=IBillRepository)
    bills.exists_for_booking.return_value = False
    bills.create.side_effect = lambda bill: bill

    result = _use_case(bills, bookings).execute(
        _data(start_time=time(10, 0), end_time=time(11, 30))
    )

    assert result.apartment_id == "R180"
    assert result.record_id == 5
    assert result.cleaning_date == date(2026, 5, 25)
    assert result.clean_hours == Decimal("1.50")
    assert result.cost == Decimal("22.50")  # 1.5 h × 15 €
    assert result.state == "Creada"
    bills.create.assert_called_once()


def test_raises_when_bill_already_exists_for_booking():
    bookings = MagicMock(spec=IBookingRepository)
    bookings.get_by_id.return_value = make_booking(record_id=5, apartment_id="R180")
    bills = MagicMock(spec=IBillRepository)
    bills.exists_for_booking.return_value = True

    with pytest.raises(BillAlreadyExists):
        _use_case(bills, bookings).execute(_data())

    bills.create.assert_not_called()


def test_raises_when_booking_not_found():
    bookings = MagicMock(spec=IBookingRepository)
    bookings.get_by_id.side_effect = BookingNotFound(5)
    bills = MagicMock(spec=IBillRepository)

    with pytest.raises(BookingNotFound):
        _use_case(bills, bookings).execute(_data())

    bills.exists_for_booking.assert_not_called()
    bills.create.assert_not_called()


def test_raises_when_end_time_not_after_start_time():
    bookings = MagicMock(spec=IBookingRepository)
    bookings.get_by_id.return_value = make_booking(record_id=5, apartment_id="R180")
    bills = MagicMock(spec=IBillRepository)
    bills.exists_for_booking.return_value = False

    with pytest.raises(DomainValidationError):
        _use_case(bills, bookings).execute(_data(start_time=time(12, 0), end_time=time(10, 0)))

    bills.create.assert_not_called()
