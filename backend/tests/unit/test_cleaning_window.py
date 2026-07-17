"""
Unit tests — regla de dominio de la ventana de limpieza.
"""

from datetime import date, datetime, time

import pytest

from domain.bookings.cleaning import (
    cleaning_window_start,
    find_previous_booking,
    sort_for_cleaning,
)
from tests.helpers import make_booking

pytestmark = pytest.mark.unit


class TestSortForCleaning:
    def test_orders_by_check_in_check_out_record_id(self):
        bookings = [
            make_booking(record_id=3, check_in=date(2026, 6, 10), check_out=date(2026, 6, 15)),
            make_booking(record_id=1, check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)),
            make_booking(record_id=2, check_in=date(2026, 6, 5), check_out=date(2026, 6, 8)),
        ]

        assert [b.record_id for b in sort_for_cleaning(bookings)] == [1, 2, 3]

    def test_discards_cancelled_and_unsaved_bookings(self):
        bookings = [
            make_booking(record_id=1, check_in=date(2026, 6, 1), check_out=date(2026, 6, 5)),
            make_booking(
                record_id=2,
                check_in=date(2026, 6, 6),
                check_out=date(2026, 6, 9),
                status="Cancelled",
            ),
            make_booking(record_id=None, check_in=date(2026, 6, 10), check_out=date(2026, 6, 12)),
        ]

        assert [b.record_id for b in sort_for_cleaning(bookings)] == [1]


class TestFindPreviousBooking:
    def test_returns_none_for_the_first_booking(self):
        first = make_booking(record_id=1, check_in=date(2026, 6, 1), check_out=date(2026, 6, 5))
        later = make_booking(record_id=2, check_in=date(2026, 6, 10), check_out=date(2026, 6, 15))

        assert find_previous_booking(first, [first, later]) is None

    def test_returns_the_immediately_earlier_booking(self):
        first = make_booking(record_id=1, check_in=date(2026, 6, 1), check_out=date(2026, 6, 5))
        middle = make_booking(record_id=2, check_in=date(2026, 6, 6), check_out=date(2026, 6, 9))
        last = make_booking(record_id=3, check_in=date(2026, 6, 10), check_out=date(2026, 6, 15))

        previous = find_previous_booking(last, [last, first, middle])

        assert previous is not None
        assert previous.record_id == 2

    def test_skips_cancelled_bookings(self):
        first = make_booking(record_id=1, check_in=date(2026, 6, 1), check_out=date(2026, 6, 5))
        cancelled = make_booking(
            record_id=2,
            check_in=date(2026, 6, 6),
            check_out=date(2026, 6, 9),
            status="Cancelled",
        )
        last = make_booking(record_id=3, check_in=date(2026, 6, 10), check_out=date(2026, 6, 15))

        previous = find_previous_booking(last, [first, cancelled, last])

        # La cancelada no ocupa el piso: la ventana la abre la salida de la reserva 1.
        assert previous is not None
        assert previous.record_id == 1


class TestCleaningWindowStart:
    def test_previous_checkout_opens_the_window(self):
        previous = make_booking(record_id=1, check_in=date(2026, 6, 1), check_out=date(2026, 6, 5))
        booking = make_booking(record_id=2, check_in=date(2026, 6, 10), check_out=date(2026, 6, 15))

        assert cleaning_window_start(booking, previous) == datetime(2026, 6, 5, 11, 0)

    def test_agreed_checkout_time_delays_the_window(self):
        previous = make_booking(
            record_id=1,
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
            check_out_time=time(13, 30),
        )
        booking = make_booking(record_id=2, check_in=date(2026, 6, 10), check_out=date(2026, 6, 15))

        assert cleaning_window_start(booking, previous) == datetime(2026, 6, 5, 13, 30)

    def test_without_previous_booking_opens_on_the_monday_of_the_check_in_week(self):
        booking = make_booking(
            record_id=1,
            check_in=date(2026, 6, 10),  # miércoles
            check_out=date(2026, 6, 15),
        )

        assert cleaning_window_start(booking, None) == datetime(2026, 6, 8, 11, 0)

    def test_a_check_in_on_monday_opens_that_same_monday(self):
        booking = make_booking(
            record_id=1,
            check_in=date(2026, 6, 8),  # lunes
            check_out=date(2026, 6, 12),
        )

        assert cleaning_window_start(booking, None) == datetime(2026, 6, 8, 11, 0)
