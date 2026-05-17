"""
Unit tests — casos de uso de lectura (queries).

El repositorio se sustituye por un MagicMock en todos los tests.
"""

from datetime import date, timedelta

import pytest

from application.bookings.queries import (
    GetBookingByIdQuery,
    GetCalendarEventsQuery,
    GetUpcomingCheckinsQuery,
    GetUpcomingCheckoutsQuery,
    ListBookingsQuery,
)
from domain.exceptions import BookingNotFound
from tests.helpers import make_booking

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# ListBookingsQuery
# ---------------------------------------------------------------------------


class TestListBookingsQuery:
    def test_with_start_and_end_date_delegates_range_to_repo(self, mock_repo):
        mock_repo.list.return_value = []
        start, end = date(2026, 6, 1), date(2026, 6, 30)

        ListBookingsQuery(mock_repo, set()).execute(start_date=start, end_date=end)

        mock_repo.list.assert_called_once_with(start_date=start, end_date=end)

    def test_with_days_calculates_end_date_from_start(self, mock_repo):
        mock_repo.list.return_value = []
        start = date(2026, 6, 1)

        ListBookingsQuery(mock_repo, set()).execute(start_date=start, days=10)

        mock_repo.list.assert_called_once_with(
            start_date=start, end_date=start + timedelta(days=10)
        )

    def test_without_filters_passes_limit_to_repo(self, mock_repo):
        mock_repo.list.return_value = []

        ListBookingsQuery(mock_repo, set()).execute(limit=5)

        mock_repo.list.assert_called_once_with(limit=5)


# ---------------------------------------------------------------------------
# GetBookingByIdQuery
# ---------------------------------------------------------------------------


class TestGetBookingByIdQuery:
    def test_found_calls_repo_with_correct_id(self, mock_repo):
        booking = make_booking(record_id=7)
        mock_repo.get_by_id.return_value = booking

        result = GetBookingByIdQuery(mock_repo, set()).execute(7)

        mock_repo.get_by_id.assert_called_once_with(7)
        assert result.record_id == 7

    def test_not_found_propagates_exception(self, mock_repo):
        mock_repo.get_by_id.side_effect = BookingNotFound(99)

        with pytest.raises(BookingNotFound):
            GetBookingByIdQuery(mock_repo, set()).execute(99)


# ---------------------------------------------------------------------------
# GetUpcomingCheckinsQuery
# ---------------------------------------------------------------------------


class TestGetUpcomingCheckinsQuery:
    def test_excludes_bookings_with_checkin_outside_window(self, mock_repo):
        today = date.today()
        soon = make_booking(
            record_id=1,
            check_in=today + timedelta(days=2),
            check_out=today + timedelta(days=6),
        )
        far = make_booking(
            record_id=2,
            check_in=today + timedelta(days=20),
            check_out=today + timedelta(days=24),
        )
        mock_repo.list.return_value = [soon, far]

        results = GetUpcomingCheckinsQuery(mock_repo, set()).execute(days=7)

        assert len(results) == 1
        assert results[0].record_id == 1

    def test_results_sorted_ascending_by_check_in(self, mock_repo):
        today = date.today()
        b1 = make_booking(
            record_id=1,
            check_in=today + timedelta(days=5),
            check_out=today + timedelta(days=9),
        )
        b2 = make_booking(
            record_id=2,
            check_in=today + timedelta(days=2),
            check_out=today + timedelta(days=6),
        )
        mock_repo.list.return_value = [b1, b2]

        results = GetUpcomingCheckinsQuery(mock_repo, set()).execute(days=7)

        assert results[0].record_id == 2  # check_in más temprano primero
        assert results[1].record_id == 1


# ---------------------------------------------------------------------------
# GetUpcomingCheckoutsQuery
# ---------------------------------------------------------------------------


class TestGetUpcomingCheckoutsQuery:
    def test_excludes_bookings_with_checkout_outside_window(self, mock_repo):
        today = date.today()
        soon = make_booking(
            record_id=1,
            check_in=today - timedelta(days=2),
            check_out=today + timedelta(days=3),
        )
        far = make_booking(
            record_id=2,
            check_in=today - timedelta(days=2),
            check_out=today + timedelta(days=15),
        )
        mock_repo.list.return_value = [soon, far]

        results = GetUpcomingCheckoutsQuery(mock_repo, set()).execute(days=7)

        assert len(results) == 1
        assert results[0].record_id == 1


# ---------------------------------------------------------------------------
# GetCalendarEventsQuery
# ---------------------------------------------------------------------------


class TestGetCalendarEventsQuery:
    def test_event_has_required_fields(self, mock_repo):
        booking = make_booking(
            record_id=10,
            booking_id="CAL-001",
            guest_name="Test User",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
        )
        mock_repo.list.return_value = [booking]

        events = GetCalendarEventsQuery(mock_repo, set()).execute(
            start_date=date(2026, 5, 1), days=90
        )

        assert len(events) == 1
        ev = events[0]
        assert ev["id"] == "booking-10"
        assert ev["title"] == "CAL-001 - Test User"
        assert ev["start"] == "2026-06-01"
        assert ev["end"] == "2026-06-05"
        assert ev["allDay"] is True
        assert "reserva" in ev["classNames"]
        assert "record_id" in ev["extendedProps"]

    def test_cancelled_booking_within_3_days_is_excluded(self, mock_repo):
        today = date.today()
        cancelled_soon = make_booking(
            record_id=1,
            status="Cancelled",
            check_in=today + timedelta(days=1),
            check_out=today + timedelta(days=5),
        )
        mock_repo.list.return_value = [cancelled_soon]

        events = GetCalendarEventsQuery(mock_repo, set()).execute(start_date=today, days=90)

        assert len(events) == 0

    def test_cancelled_booking_beyond_3_days_is_included_with_cancelled_class(self, mock_repo):
        today = date.today()
        cancelled_far = make_booking(
            record_id=2,
            status="Cancelled",
            check_in=today + timedelta(days=10),
            check_out=today + timedelta(days=14),
        )
        mock_repo.list.return_value = [cancelled_far]

        events = GetCalendarEventsQuery(mock_repo, set()).execute(start_date=today, days=90)

        assert len(events) == 1
        assert "cancelled" in events[0]["classNames"]
