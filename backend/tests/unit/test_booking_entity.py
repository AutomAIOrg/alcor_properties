"""
Unit tests — entidad de dominio Booking y excepciones de dominio.

Sin I/O, sin mocks, sin dependencias externas.
"""

import pytest
from datetime import date, timedelta

from domain.bookings.entity import Booking
from domain.exceptions import BookingConflict, BookingNotFound, DomainValidationError
from tests.helpers import make_booking

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Creación y validación de campos
# ---------------------------------------------------------------------------


class TestBookingCreation:
    def test_valid_booking_is_created(self):
        b = make_booking()
        assert b.booking_id == "TEST-001"
        assert b.guest_name == "Ana García"
        assert b.nights == 4

    def test_check_out_before_check_in_raises_value_error(self):
        with pytest.raises(ValueError, match="check_out debe ser estrictamente posterior"):
            Booking(
                booking_id="B",
                guest_name="X",
                check_in=date(2026, 6, 5),
                check_out=date(2026, 6, 1),
                nights=1,
            )

    def test_check_out_equal_check_in_raises_value_error(self):
        with pytest.raises(ValueError):
            Booking(
                booking_id="B",
                guest_name="X",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 1),
                nights=1,
            )

    def test_nights_auto_corrected_to_real_date_diff(self):
        """nights siempre se deriva de las fechas, ignorando el valor suministrado."""
        b = Booking(
            booking_id="B",
            guest_name="X",
            check_in=date(2026, 6, 1),
            check_out=date(2026, 6, 4),
            nights=999,
        )
        assert b.nights == 3


# ---------------------------------------------------------------------------
# is_active()
# ---------------------------------------------------------------------------


class TestIsActive:
    def setup_method(self):
        self.b = make_booking(check_in=date(2026, 6, 1), check_out=date(2026, 6, 5))

    def test_active_during_stay(self):
        assert self.b.is_active(reference_date=date(2026, 6, 3))

    def test_active_on_check_in_day(self):
        assert self.b.is_active(reference_date=date(2026, 6, 1))

    def test_active_on_check_out_day(self):
        assert self.b.is_active(reference_date=date(2026, 6, 5))

    def test_not_active_before_check_in(self):
        assert not self.b.is_active(reference_date=date(2026, 5, 31))

    def test_not_active_after_check_out(self):
        assert not self.b.is_active(reference_date=date(2026, 6, 6))


# ---------------------------------------------------------------------------
# is_cancelled()
# ---------------------------------------------------------------------------


class TestIsCancelled:
    @pytest.mark.parametrize("status", ["Cancelled", "CANCELLED", "cancelled"])
    def test_cancelled_for_any_case_variant(self, status):
        assert make_booking(status=status).is_cancelled()

    def test_not_cancelled_for_non_cancelled_status(self):
        assert not make_booking(status="Confirmed").is_cancelled()


# ---------------------------------------------------------------------------
# has_upcoming_checkin() / has_upcoming_checkout()
# ---------------------------------------------------------------------------


class TestUpcomingCheckinCheckout:
    def test_checkin_within_range(self):
        ref = date(2026, 6, 1)
        b = make_booking(check_in=date(2026, 6, 5), check_out=date(2026, 6, 10))
        assert b.has_upcoming_checkin(days=7, reference_date=ref)

    def test_checkin_outside_range(self):
        ref = date(2026, 6, 1)
        b = make_booking(check_in=date(2026, 6, 15), check_out=date(2026, 6, 20))
        assert not b.has_upcoming_checkin(days=7, reference_date=ref)

    def test_checkout_within_range(self):
        ref = date(2026, 6, 1)
        b = make_booking(check_in=date(2026, 6, 1), check_out=date(2026, 6, 7))
        assert b.has_upcoming_checkout(days=7, reference_date=ref)

    def test_checkout_outside_range(self):
        ref = date(2026, 6, 1)
        b = make_booking(check_in=date(2026, 6, 1), check_out=date(2026, 6, 15))
        assert not b.has_upcoming_checkout(days=7, reference_date=ref)


# ---------------------------------------------------------------------------
# Excepciones de dominio
# ---------------------------------------------------------------------------


class TestDomainExceptions:
    def test_booking_not_found_includes_id_in_message(self):
        assert "42" in str(BookingNotFound(42))

    def test_booking_conflict_includes_dates_in_message(self):
        exc = BookingConflict("2026-06-01", "2026-06-05")
        assert "2026-06-01" in str(exc)
        assert "2026-06-05" in str(exc)

    def test_domain_validation_error_propagates_message(self):
        assert "regla violada" in str(DomainValidationError("regla violada"))
