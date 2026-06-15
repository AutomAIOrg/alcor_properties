"""
Unit tests — casos de uso de escritura (Create, Update, Delete).

El repositorio se sustituye por un MagicMock en todos los tests.
"""

from datetime import date

import pytest

from application.bookings.commands import (
    BookingUpdateData,
    CreateBookingUseCase,
    DeleteBookingUseCase,
    UpdateBookingUseCase,
)
from domain.exceptions import BookingConflict, BookingNotFound
from tests.helpers import make_booking

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# CreateBookingUseCase
# ---------------------------------------------------------------------------


class TestCreateBookingUseCase:
    def test_electric_allowance_applied_when_apartment_id_matches(self, mock_repo):
        booking = make_booking(
            apartment_id="ELEC-001",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 4),
        )
        mock_repo.create.return_value = booking

        result = CreateBookingUseCase(mock_repo, {"ELEC-001"}).execute(booking)

        assert result.electric_allowance == booking.nights * 4.0

    def test_electric_allowance_is_none_when_apartment_id_not_in_electric_ids(self, mock_repo):
        booking = make_booking(apartment_id="NORMAL-001")
        mock_repo.create.return_value = booking

        result = CreateBookingUseCase(mock_repo, {"ELEC-001"}).execute(booking)

        assert result.electric_allowance is None

    def test_raises_booking_conflict_when_active_booking_overlaps(self, mock_repo):
        booking = make_booking(apartment_id="R180")
        mock_repo.find_overlapping_active.return_value = True

        with pytest.raises(BookingConflict):
            CreateBookingUseCase(mock_repo, set()).execute(booking)

        mock_repo.create.assert_not_called()


# ---------------------------------------------------------------------------
# UpdateBookingUseCase
# ---------------------------------------------------------------------------


class TestUpdateBookingUseCase:
    def test_partial_merge_applies_only_provided_fields(self, mock_repo):
        existing = make_booking(
            record_id=1,
            guest_name="Ana García",
            status="Confirmed",
            email="ana@example.com",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 5),
        )
        mock_repo.get_by_id.return_value = existing
        mock_repo.update.side_effect = lambda booking: booking

        result = UpdateBookingUseCase(mock_repo, set()).execute(
            1, BookingUpdateData(guest_name="Carlos López")
        )

        assert result.guest_name == "Carlos López"
        assert result.status == "Confirmed"  # campo no enviado se conserva
        assert result.email == "ana@example.com"

    def test_partial_merge_clears_optional_fields_when_none_is_provided(self, mock_repo):
        existing = make_booking(
            record_id=1,
            email="ana@example.com",
            phone="+34 600 000 000",
            notes="Llegada tarde",
        )
        mock_repo.get_by_id.return_value = existing
        mock_repo.update.side_effect = lambda booking: booking

        result = UpdateBookingUseCase(mock_repo, set()).execute(1, BookingUpdateData(email=None))

        assert result.email is None
        assert result.phone == "+34 600 000 000"
        assert result.notes == "Llegada tarde"

    def test_propagates_booking_not_found_from_repository(self, mock_repo):
        mock_repo.get_by_id.side_effect = BookingNotFound(99)

        with pytest.raises(BookingNotFound):
            UpdateBookingUseCase(mock_repo, set()).execute(99, BookingUpdateData())


# ---------------------------------------------------------------------------
# DeleteBookingUseCase
# ---------------------------------------------------------------------------


class TestDeleteBookingUseCase:
    def test_calls_repository_delete_with_correct_id(self, mock_repo):
        DeleteBookingUseCase(mock_repo).execute(5)

        mock_repo.delete.assert_called_once_with(5)

    def test_propagates_booking_not_found_from_repository(self, mock_repo):
        mock_repo.delete.side_effect = BookingNotFound(99)

        with pytest.raises(BookingNotFound):
            DeleteBookingUseCase(mock_repo).execute(99)
