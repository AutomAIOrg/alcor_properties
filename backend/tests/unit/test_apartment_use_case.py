"""
Unit tests — casos de uso SearchApartmentsUseCase y GetApartmentByIdUseCase.

El repositorio se sustituye por un MagicMock en todos los tests.
"""

from datetime import date

import pytest

from application.apartments.use_cases import (
    GetApartmentByIdUseCase,
    GetApartmentStatsUseCase,
    SearchApartmentsUseCase,
)
from domain.apartments.filters import ApartmentSearchFilters
from tests.helpers import make_apartment, make_booking

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# SearchApartments
# ---------------------------------------------------------------------------


class TestSearchApartments:
    def test_delegates_filters_to_repository(self, mock_apartment_repo):
        filters = ApartmentSearchFilters()
        mock_apartment_repo.search_apartments.return_value = []

        SearchApartmentsUseCase(mock_apartment_repo).execute(filters)

        mock_apartment_repo.search_apartments.assert_called_once_with(filters)

    def test_returns_list_from_repository(self, mock_apartment_repo):
        apt = make_apartment()
        mock_apartment_repo.search_apartments.return_value = [apt]

        result = SearchApartmentsUseCase(mock_apartment_repo).execute(ApartmentSearchFilters())

        assert result == [apt]

    def test_returns_empty_list_when_no_matches(self, mock_apartment_repo):
        mock_apartment_repo.search_apartments.return_value = []

        result = SearchApartmentsUseCase(mock_apartment_repo).execute(ApartmentSearchFilters())

        assert result == []


# ---------------------------------------------------------------------------
# GetApartmentByIdUseCase
# ---------------------------------------------------------------------------


class TestGetApartmentByIdUseCase:
    def test_returns_apartment_when_found(self, mock_apartment_repo):
        apt = make_apartment(apartment_id="R180")
        mock_apartment_repo.get_by_apartment_id.return_value = apt

        result = GetApartmentByIdUseCase(mock_apartment_repo).execute("R180")

        mock_apartment_repo.get_by_apartment_id.assert_called_once_with("R180")
        assert result == apt

    def test_returns_none_when_not_found(self, mock_apartment_repo):
        mock_apartment_repo.get_by_apartment_id.return_value = None

        result = GetApartmentByIdUseCase(mock_apartment_repo).execute("UNKNOWN")

        assert result is None

    def test_empty_apartment_id_raises_value_error(self, mock_apartment_repo):
        with pytest.raises(ValueError):
            GetApartmentByIdUseCase(mock_apartment_repo).execute("")

    def test_whitespace_apartment_id_raises_value_error(self, mock_apartment_repo):
        with pytest.raises(ValueError):
            GetApartmentByIdUseCase(mock_apartment_repo).execute("   ")

    def test_apartment_id_is_stripped_before_calling_repository(self, mock_apartment_repo):
        apt = make_apartment(apartment_id="R180")
        mock_apartment_repo.get_by_apartment_id.return_value = apt

        GetApartmentByIdUseCase(mock_apartment_repo).execute("  R180  ")

        mock_apartment_repo.get_by_apartment_id.assert_called_once_with("R180")


# ---------------------------------------------------------------------------
# GetApartmentStatsUseCase
# ---------------------------------------------------------------------------


class TestGetApartmentStatsUseCase:
    def test_filtered_range_occupancy_uses_only_overlapping_nights(
        self,
        mock_apartment_repo,
        mock_repo,
    ):
        apartment = make_apartment(apartment_id="R180")
        booking = make_booking(
            apartment_id="R180",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 20),
        )
        mock_apartment_repo.get_by_apartment_id.return_value = apartment
        mock_repo.list.side_effect = [[booking], [booking]]

        result = GetApartmentStatsUseCase(mock_apartment_repo, mock_repo, set()).execute(
            apartment_id="R180",
            start_date=date(2026, 6, 10),
            end_date=date(2026, 6, 15),
        )

        assert result["filtered_range"]["occupancy_pct"] == 100.0

    def test_filtered_range_occupancy_ignores_cancelled_bookings(
        self,
        mock_apartment_repo,
        mock_repo,
    ):
        apartment = make_apartment(apartment_id="R180")
        booking = make_booking(
            apartment_id="R180",
            status="Cancelled",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 20),
        )
        mock_apartment_repo.get_by_apartment_id.return_value = apartment
        mock_repo.list.side_effect = [[booking], [booking]]

        result = GetApartmentStatsUseCase(mock_apartment_repo, mock_repo, set()).execute(
            apartment_id="R180",
            start_date=date(2026, 6, 10),
            end_date=date(2026, 6, 15),
        )

        assert result["filtered_range"]["occupancy_pct"] == 0.0

    def test_by_year_splits_cross_year_booking_nights_and_amounts(
        self,
        mock_apartment_repo,
        mock_repo,
    ):
        apartment = make_apartment(apartment_id="R180")
        booking = make_booking(
            apartment_id="R180",
            check_in=date(2026, 12, 30),
            check_out=date(2027, 1, 3),
            price=400,
            charges=40,
        )
        mock_apartment_repo.get_by_apartment_id.return_value = apartment
        mock_repo.list.side_effect = [[booking], [booking]]

        result = GetApartmentStatsUseCase(mock_apartment_repo, mock_repo, {"R180"}).execute(
            apartment_id="R180",
            start_date=date(2026, 12, 1),
            end_date=date(2027, 2, 1),
        )

        by_year = {item["year"]: item for item in result["by_year"]}
        assert by_year[2026]["total_nights"] == 2
        assert by_year[2026]["total_revenue"] == 200.0
        assert by_year[2026]["total_charges"] == 20.0
        assert by_year[2026]["total_electric_allowance"] == 8.0
        assert by_year[2027]["total_nights"] == 2
        assert by_year[2027]["total_revenue"] == 200.0
        assert by_year[2027]["total_charges"] == 20.0
        assert by_year[2027]["total_electric_allowance"] == 8.0

    def test_by_year_counts_cancelled_cross_year_booking_without_occupancy(
        self,
        mock_apartment_repo,
        mock_repo,
    ):
        apartment = make_apartment(apartment_id="R180")
        booking = make_booking(
            apartment_id="R180",
            status="Cancelled",
            check_in=date(2026, 12, 30),
            check_out=date(2027, 1, 3),
            price=400,
        )
        mock_apartment_repo.get_by_apartment_id.return_value = apartment
        mock_repo.list.side_effect = [[booking], [booking]]

        result = GetApartmentStatsUseCase(mock_apartment_repo, mock_repo, set()).execute(
            apartment_id="R180",
            start_date=date(2026, 12, 1),
            end_date=date(2027, 2, 1),
        )

        by_year = {item["year"]: item for item in result["by_year"]}
        assert by_year[2026]["total_bookings"] == 1
        assert by_year[2026]["cancelled_bookings"] == 1
        assert by_year[2026]["total_nights"] == 0
        assert by_year[2026]["total_revenue"] is None
        assert by_year[2027]["total_bookings"] == 1
        assert by_year[2027]["cancelled_bookings"] == 1
        assert by_year[2027]["total_nights"] == 0
        assert by_year[2027]["total_revenue"] is None
