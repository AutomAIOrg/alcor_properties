"""
Unit tests — cálculo de ventanas de limpieza.
"""

from datetime import date

import pytest

from application.bookings.queries import (
    GetCleaningOpportunitiesUseCase,
    _build_cleaning_opportunities,
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


class TestGetCleaningOpportunitiesUseCase:
    def test_delegates_to_repository_list(self, mock_repo):
        mock_repo.list.return_value = []
        use_case = GetCleaningOpportunitiesUseCase(mock_repo)

        assert use_case.execute() == []
        mock_repo.list.assert_called_once_with()
