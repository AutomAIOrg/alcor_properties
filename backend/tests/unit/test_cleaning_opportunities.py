"""
Unit tests — cálculo de ventanas de limpieza.
"""

from datetime import date

import pytest

from application.bookings.queries import (
    GetCleaningOpportunitiesUseCase,
    _build_cleaning_opportunities,
    _cleaning_operational_range,
    _cleaning_window_overlaps_range,
)
from tests.helpers import make_booking

pytestmark = pytest.mark.unit


class TestBuildCleaningOpportunities:
    def test_excludes_cancelled_bookings(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
            ),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 6, 10),
                check_out=date(2026, 6, 15),
                status="Cancelled",
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert len(opportunities) == 1
        assert opportunities[0].source_booking_record_id == 1
        assert opportunities[0].available_until is None

    def test_skips_bookings_without_record_id(self):
        bookings = [
            make_booking(record_id=None, apartment_id="R180"),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 6, 10),
                check_out=date(2026, 6, 15),
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert len(opportunities) == 1
        assert opportunities[0].source_booking_record_id == 2

    def test_sets_available_until_to_next_booking_check_in(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
            ),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 6, 10),
                check_out=date(2026, 6, 15),
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert len(opportunities) == 2
        first, second = opportunities
        assert first.available_from == date(2026, 6, 5)
        assert first.available_until == date(2026, 6, 10)
        assert second.available_from == date(2026, 6, 15)
        assert second.available_until is None

    def test_groups_by_apartment(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
            ),
            make_booking(
                record_id=2,
                apartment_id="R200",
                check_in=date(2026, 6, 2),
                check_out=date(2026, 6, 7),
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert len(opportunities) == 2
        assert {opportunity.apartment_id for opportunity in opportunities} == {"R180", "R200"}
        assert all(opportunity.available_until is None for opportunity in opportunities)

    def test_orders_bookings_within_apartment_by_check_in_check_out_record_id(self):
        bookings = [
            make_booking(
                record_id=3,
                apartment_id="R180",
                check_in=date(2026, 6, 10),
                check_out=date(2026, 6, 15),
            ),
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
            ),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 6, 5),
                check_out=date(2026, 6, 8),
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert [opportunity.source_booking_record_id for opportunity in opportunities] == [1, 2, 3]
        assert opportunities[0].available_until == date(2026, 6, 5)
        assert opportunities[1].available_until == date(2026, 6, 10)
        assert opportunities[2].available_until is None

    def test_sorts_opportunities_with_available_until_before_open_ended(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
            ),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 6, 20),
                check_out=date(2026, 6, 25),
            ),
            make_booking(
                record_id=3,
                apartment_id="R200",
                check_in=date(2026, 6, 2),
                check_out=date(2026, 6, 7),
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert opportunities[0].available_until == date(2026, 6, 20)
        assert opportunities[1].available_until is None
        assert opportunities[2].available_until is None

    def test_trims_comments_from_notes(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
                notes="  dejar llaves en conserjería  ",
            )
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert opportunities[0].comments == "dejar llaves en conserjería"

    def test_empty_comments_when_notes_are_none(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
                notes=None,
            )
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert opportunities[0].comments == ""


class TestCleaningOperationalRange:
    def test_returns_current_week_plus_three_following(self):
        range_start, range_end = _cleaning_operational_range(date(2026, 6, 18))

        assert range_start == date(2026, 6, 15)
        assert range_end == date(2026, 7, 12)


class TestCleaningWindowOverlapsRange:
    def test_includes_window_with_check_in_inside_range(self):
        assert _cleaning_window_overlaps_range(
            date(2026, 6, 2),
            date(2026, 6, 18),
            date(2026, 6, 15),
            date(2026, 7, 12),
        )

    def test_excludes_open_ended_window_before_range(self):
        assert not _cleaning_window_overlaps_range(
            date(2026, 5, 1),
            None,
            date(2026, 6, 15),
            date(2026, 7, 12),
        )

    def test_includes_open_ended_window_with_checkout_in_range(self):
        assert _cleaning_window_overlaps_range(
            date(2026, 6, 20),
            None,
            date(2026, 6, 15),
            date(2026, 7, 12),
        )


class TestGetCleaningOpportunitiesUseCase:
    def test_delegates_to_repository_with_operational_date_range(self, mock_repo):
        mock_repo.list.return_value = []
        use_case = GetCleaningOpportunitiesUseCase(mock_repo)
        reference_date = date(2026, 6, 18)

        assert use_case.execute(reference_date=reference_date) == []
        mock_repo.list.assert_called_once_with(
            start_date=date(2026, 5, 18),
            end_date=date(2026, 10, 10),
        )

    def test_excludes_windows_outside_operational_range(self, mock_repo):
        mock_repo.list.return_value = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 4, 1),
                check_out=date(2026, 4, 5),
            ),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 4, 10),
                check_out=date(2026, 4, 15),
            ),
            make_booking(
                record_id=3,
                apartment_id="R200",
                check_in=date(2026, 8, 1),
                check_out=date(2026, 8, 5),
            ),
        ]
        use_case = GetCleaningOpportunitiesUseCase(mock_repo)

        assert use_case.execute(reference_date=date(2026, 6, 18)) == []

    def test_sets_available_until_when_next_booking_is_beyond_operational_range(self):
        """La ventana dentro del rango debe conocer su siguiente check-in aunque caiga
        después de range_end (gracias al lookahead del fetch)."""

        class _FilteringRepo:
            """Repo falso con la misma semántica de solapamiento que el real."""

            def __init__(self, bookings):
                self._bookings = bookings

            def list(self, start_date=None, end_date=None, **_):
                return [
                    b
                    for b in self._bookings
                    if b.check_in <= end_date and b.check_out >= start_date
                ]

        source = make_booking(
            record_id=1,
            apartment_id="R180",
            check_in=date(2026, 7, 5),
            check_out=date(2026, 7, 10),  # checkout dentro del rango operativo
        )
        next_booking = make_booking(
            record_id=2,
            apartment_id="R180",
            check_in=date(2026, 7, 20),  # check-in pasado range_end (2026-07-12)
            check_out=date(2026, 7, 25),
        )
        use_case = GetCleaningOpportunitiesUseCase(_FilteringRepo([source, next_booking]))

        opportunities = use_case.execute(reference_date=date(2026, 6, 18))

        window = next(o for o in opportunities if o.source_booking_record_id == 1)
        assert window.available_until == date(2026, 7, 20)
