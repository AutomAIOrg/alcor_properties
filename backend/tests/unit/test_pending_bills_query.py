"""
Unit tests — consulta de facturas pendientes (limpiezas facturables sin factura).

Referencia temporal fija: miércoles 2026-06-24 12:00. El lunes de esa semana es 2026-06-22.
La hora de salida por defecto es 11:00.
"""

from datetime import date, datetime
from unittest.mock import MagicMock

import pytest

from application.bills.queries import ListPendingBillsQuery
from domain.bills.repository import IBillRepository
from domain.bookings.repository import IBookingRepository
from tests.helpers import make_booking

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 6, 24, 12, 0)  # miércoles, 12:00
_WEEK_START = date(2026, 6, 22)  # lunes de esa semana


def _query(
    bookings: list,
    billed_ids: set[int] | None = None,
    bill_states: dict[int, str] | None = None,
) -> ListPendingBillsQuery:
    booking_repo = MagicMock(spec=IBookingRepository)
    booking_repo.list.return_value = bookings
    bill_repo = MagicMock(spec=IBillRepository)
    bill_repo.list_billed_booking_ids.return_value = billed_ids or set()
    bill_repo.get_bill_states_by_booking.return_value = bill_states or {}
    return ListPendingBillsQuery(booking_repo, bill_repo)


def test_includes_past_checkout_in_current_week():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 23))]

    result = _query(bookings).execute(reference_datetime=_NOW)

    assert len(result) == 1
    assert result[0].record_id == 1
    assert result[0].state == "Pendiente"
    assert result[0].bill_id is None
    assert result[0].cleaning_date == date(2026, 6, 23)


def test_includes_today_checkout_after_default_checkout_time():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 24))]

    result = _query(bookings).execute(reference_datetime=datetime(2026, 6, 24, 11, 30))

    assert len(result) == 1


def test_excludes_today_checkout_before_default_checkout_time():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 24))]

    result = _query(bookings).execute(reference_datetime=datetime(2026, 6, 24, 9, 0))

    assert result == []


def test_excludes_future_checkout():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 24), check_out=date(2026, 6, 26))]

    result = _query(bookings).execute(reference_datetime=_NOW)

    assert result == []


def test_excludes_checkout_before_current_week():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 12), check_out=date(2026, 6, 15))]

    result = _query(bookings).execute(reference_datetime=_NOW)

    assert result == []


def test_includes_checkout_exactly_on_week_start_monday():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 19), check_out=_WEEK_START)]

    result = _query(bookings).execute(reference_datetime=_NOW)

    assert len(result) == 1
    assert result[0].cleaning_date == _WEEK_START


def test_excludes_already_billed_bookings():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 23))]

    result = _query(bookings, billed_ids={1}).execute(reference_datetime=_NOW)

    assert result == []


def test_excludes_cancelled_bookings():
    bookings = [
        make_booking(
            record_id=1,
            check_in=date(2026, 6, 20),
            check_out=date(2026, 6, 23),
            status="Cancelled",
        )
    ]

    result = _query(bookings).execute(reference_datetime=_NOW)

    assert result == []


def test_pending_without_prior_bill_is_not_marked_cancelled():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 23))]

    result = _query(bookings).execute(reference_datetime=_NOW)

    assert len(result) == 1
    assert result[0].previously_cancelled is False


def test_pending_with_cancelled_bill_is_flagged():
    bookings = [make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 23))]

    # La reserva reaparece como pendiente (las canceladas no cuentan como facturadas)
    # y debe marcarse como 'previously_cancelled' para que la UI lo indique.
    result = _query(bookings, bill_states={1: "Cancelada"}).execute(reference_datetime=_NOW)

    assert len(result) == 1
    assert result[0].previously_cancelled is True


def test_date_to_filters_out_later_checkouts():
    bookings = [
        make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 22)),
        make_booking(record_id=2, check_in=date(2026, 6, 21), check_out=date(2026, 6, 23)),
    ]

    result = _query(bookings).execute(reference_datetime=_NOW, date_to=date(2026, 6, 22))

    assert [bill.record_id for bill in result] == [1]


def test_results_sorted_by_checkout_descending():
    bookings = [
        make_booking(record_id=1, check_in=date(2026, 6, 20), check_out=date(2026, 6, 22)),
        make_booking(record_id=2, check_in=date(2026, 6, 21), check_out=date(2026, 6, 24)),
        make_booking(record_id=3, check_in=date(2026, 6, 20), check_out=date(2026, 6, 23)),
    ]

    result = _query(bookings).execute(reference_datetime=_NOW)

    assert [bill.record_id for bill in result] == [2, 3, 1]


def test_apartment_filter_forwarded_to_repository():
    query = _query([])
    query.execute(apartment_id="R180", reference_datetime=_NOW)

    _, kwargs = query._bookings.list.call_args
    assert kwargs["apartment_id"] == "R180"
