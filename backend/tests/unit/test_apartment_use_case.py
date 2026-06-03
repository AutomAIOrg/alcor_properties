"""
Unit tests — casos de uso SearchApartmentsQuery y GetApartmentByBookingIdQuery.

El repositorio se sustituye por un MagicMock en todos los tests.
"""

import pytest

from application.apartments.queries import GetApartmentByBookingIdQuery, SearchApartmentsQuery
from domain.apartments.filters import ApartmentSearchFilters
from tests.helpers import make_apartment

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# SearchApartments
# ---------------------------------------------------------------------------


class TestSearchApartments:
    def test_delegates_filters_to_repository(self, mock_apartment_repo):
        filters = ApartmentSearchFilters()
        mock_apartment_repo.search_apartments.return_value = []

        SearchApartmentsQuery(mock_apartment_repo).execute(filters)

        mock_apartment_repo.search_apartments.assert_called_once_with(filters)

    def test_returns_list_from_repository(self, mock_apartment_repo):
        apt = make_apartment()
        mock_apartment_repo.search_apartments.return_value = [apt]

        result = SearchApartmentsQuery(mock_apartment_repo).execute(ApartmentSearchFilters())

        assert result == [apt]

    def test_returns_empty_list_when_no_matches(self, mock_apartment_repo):
        mock_apartment_repo.search_apartments.return_value = []

        result = SearchApartmentsQuery(mock_apartment_repo).execute(ApartmentSearchFilters())

        assert result == []


# ---------------------------------------------------------------------------
# GetApartmentByBookingIdQuery
# ---------------------------------------------------------------------------


class TestGetApartmentByBookingIdQuery:
    def test_returns_apartment_when_found(self, mock_apartment_repo):
        apt = make_apartment(booking_id="R180")
        mock_apartment_repo.get_by_booking_id.return_value = apt

        result = GetApartmentByBookingIdQuery(mock_apartment_repo).execute("R180")

        mock_apartment_repo.get_by_booking_id.assert_called_once_with("R180")
        assert result == apt

    def test_returns_none_when_not_found(self, mock_apartment_repo):
        mock_apartment_repo.get_by_booking_id.return_value = None

        result = GetApartmentByBookingIdQuery(mock_apartment_repo).execute("UNKNOWN")

        assert result is None

    def test_empty_booking_id_raises_value_error(self, mock_apartment_repo):
        with pytest.raises(ValueError):
            GetApartmentByBookingIdQuery(mock_apartment_repo).execute("")

    def test_whitespace_booking_id_raises_value_error(self, mock_apartment_repo):
        with pytest.raises(ValueError):
            GetApartmentByBookingIdQuery(mock_apartment_repo).execute("   ")

    def test_booking_id_is_stripped_before_calling_repository(self, mock_apartment_repo):
        apt = make_apartment(booking_id="R180")
        mock_apartment_repo.get_by_booking_id.return_value = apt

        GetApartmentByBookingIdQuery(mock_apartment_repo).execute("  R180  ")

        mock_apartment_repo.get_by_booking_id.assert_called_once_with("R180")
