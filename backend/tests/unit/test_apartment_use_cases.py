"""
Unit tests — casos de uso de apartamentos.

Sin I/O, mocks de repositorios.
"""

from datetime import date, timedelta

import pytest

from application.apartments.use_cases import DeleteApartmentUseCase
from domain.exceptions import ApartmentHasBookingsError, ApartmentNotFoundError
from tests.helpers import make_apartment, make_booking

pytestmark = pytest.mark.unit


class TestDeleteApartmentUseCase:
    def test_deletes_when_no_blocking_bookings(self, mock_apartment_repo, mock_repo):
        apartment = make_apartment(apartment_id="R180")
        mock_apartment_repo.get_by_apartment_id.return_value = apartment
        mock_repo.get_all_by_apartment_id.return_value = []

        DeleteApartmentUseCase(mock_apartment_repo, mock_repo).execute("R180")

        mock_repo.get_all_by_apartment_id.assert_called_once_with("R180")
        mock_apartment_repo.delete_apartment.assert_called_once_with(apartment)

    def test_raises_not_found_when_apartment_missing(self, mock_apartment_repo, mock_repo):
        mock_apartment_repo.get_by_apartment_id.return_value = None

        with pytest.raises(ApartmentNotFoundError):
            DeleteApartmentUseCase(mock_apartment_repo, mock_repo).execute("UNKNOWN")

        mock_repo.get_all_by_apartment_id.assert_not_called()
        mock_apartment_repo.delete_apartment.assert_not_called()

    def test_raises_has_bookings_when_future_confirmed_booking(
        self, mock_apartment_repo, mock_repo
    ):
        apartment = make_apartment(apartment_id="R180")
        mock_apartment_repo.get_by_apartment_id.return_value = apartment
        today = date.today()
        mock_repo.get_all_by_apartment_id.return_value = [
            make_booking(
                apartment_id="R180",
                check_in=today + timedelta(days=10),
                check_out=today + timedelta(days=15),
                status="Confirmed",
            )
        ]

        with pytest.raises(ApartmentHasBookingsError):
            DeleteApartmentUseCase(mock_apartment_repo, mock_repo).execute("R180")

        mock_apartment_repo.delete_apartment.assert_not_called()

    def test_allows_delete_with_cancelled_future_booking(self, mock_apartment_repo, mock_repo):
        apartment = make_apartment(apartment_id="R180")
        mock_apartment_repo.get_by_apartment_id.return_value = apartment
        today = date.today()
        mock_repo.get_all_by_apartment_id.return_value = [
            make_booking(
                apartment_id="R180",
                check_in=today + timedelta(days=10),
                check_out=today + timedelta(days=15),
                status="cancelled",
            )
        ]

        DeleteApartmentUseCase(mock_apartment_repo, mock_repo).execute("R180")

        mock_apartment_repo.delete_apartment.assert_called_once_with(apartment)

    def test_allows_delete_with_past_confirmed_booking(self, mock_apartment_repo, mock_repo):
        apartment = make_apartment(apartment_id="R180")
        mock_apartment_repo.get_by_apartment_id.return_value = apartment
        today = date.today()
        mock_repo.get_all_by_apartment_id.return_value = [
            make_booking(
                apartment_id="R180",
                check_in=today - timedelta(days=20),
                check_out=today - timedelta(days=15),
                status="Confirmed",
            )
        ]

        DeleteApartmentUseCase(mock_apartment_repo, mock_repo).execute("R180")

        mock_apartment_repo.delete_apartment.assert_called_once_with(apartment)
