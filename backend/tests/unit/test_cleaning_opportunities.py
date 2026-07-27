"""
Unit tests — cálculo de ventanas de limpieza.
"""

from datetime import date, datetime, time

import pytest

from application.bookings.queries import (
    GetCleaningOpportunitiesUseCase,
    _build_cleaning_opportunities,
    _cleaning_operational_range,
    _cleaning_window_overlaps_range,
)
from tests.helpers import make_apartment, make_booking

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

        # La cancelada no llega a entrar, así que no hay nada que preparar para ella.
        assert len(opportunities) == 1
        assert opportunities[0].source_booking_record_id == 1
        assert opportunities[0].available_until == date(2026, 6, 1)

    def test_enriches_with_apartment_address_and_description(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R106",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
            ),
        ]
        apartments_by_id = {
            "R106": make_apartment(
                apartment_id="R106",
                address="C/ Raquero 6 Bloque 3",
                apartment_description="Porto Fino",
            ),
        }

        opportunities = _build_cleaning_opportunities(bookings, apartments_by_id=apartments_by_id)

        assert opportunities[0].address == "C/ Raquero 6 Bloque 3"
        assert opportunities[0].apartment_description == "Porto Fino"

    def test_apartment_data_is_none_when_not_found(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R999",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings, apartments_by_id={})

        assert opportunities[0].address is None
        assert opportunities[0].apartment_description is None

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

    def test_window_runs_from_previous_checkout_to_own_check_in(self):
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

        # Una limpieza por cada entrada: la de la reserva 1 (sin anterior, arranca el lunes de
        # su semana) y la que prepara la entrada de la 2 (la abre la salida de la 1).
        assert len(opportunities) == 2
        first, second = opportunities
        assert first.source_booking_record_id == 1
        # Booking 1: sin anterior → available_from = lunes de su semana = 2026-06-01 (lunes)
        assert first.available_from == date(2026, 6, 1)
        assert first.available_until == date(2026, 6, 1)
        assert first.previous_booking_record_id is None
        assert second.source_booking_record_id == 2
        # Booking 2: check-out anterior (2026-06-05, viernes) y check-in (2026-06-10, miércoles)
        # NO están en la misma semana (semana1: lun1-dom7, semana2: lun8-dom14).
        # Tampoco el check-out está en la semana anterior (one_week_before_monday = 2026-06-01).
        # 2026-06-05 < 2026-06-01? No, 2026-06-05 >= 2026-06-01, SÍ está en la semana anterior.
        # Entonces sí se usa el check-out anterior.
        assert second.available_from == date(2026, 6, 5)
        assert second.available_until == date(2026, 6, 10)
        assert second.previous_booking_record_id == 1

    def test_head_window_opens_on_the_monday_of_the_check_in_week(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 10),  # miércoles
                check_out=date(2026, 6, 15),
            )
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        # Sin reserva anterior no hay salida que esperar: la ventana abre el lunes a la hora
        # estándar de salida.
        assert len(opportunities) == 1
        assert opportunities[0].available_from == date(2026, 6, 8)
        assert opportunities[0].available_from_time == time(11, 0)
        assert opportunities[0].available_until == date(2026, 6, 10)
        assert opportunities[0].previous_booking_record_id is None

    def test_head_window_can_bill_flips_at_monday_checkout_time(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 10),
                check_out=date(2026, 6, 15),
            )
        ]

        before = _build_cleaning_opportunities(
            bookings, reference_datetime=datetime(2026, 6, 8, 10, 59)
        )
        at = _build_cleaning_opportunities(bookings, reference_datetime=datetime(2026, 6, 8, 11, 0))

        assert not before[0].can_bill
        assert at[0].can_bill

    def test_persons_and_nights_come_from_the_arriving_booking(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
                persons=2,
            ),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 6, 10),
                check_out=date(2026, 6, 15),
                persons=4,
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        # La limpieza prepara la entrada: la ocupación que importa es la de quien llega.
        assert opportunities[1].source_booking_record_id == 2
        assert opportunities[1].persons == 4
        assert opportunities[1].nights == 5

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
        assert all(opportunity.previous_booking_record_id is None for opportunity in opportunities)

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

        # Cada reserva ancla la limpieza de su propia entrada; la cadena encadena las ventanas.
        assert [opportunity.source_booking_record_id for opportunity in opportunities] == [1, 2, 3]
        assert [opportunity.previous_booking_record_id for opportunity in opportunities] == [
            None,
            1,
            2,
        ]
        assert opportunities[0].available_until == date(2026, 6, 1)
        assert opportunities[1].available_until == date(2026, 6, 5)
        assert opportunities[2].available_until == date(2026, 6, 10)

    def test_sorts_opportunities_by_check_in(self):
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

        assert [opportunity.available_until for opportunity in opportunities] == [
            date(2026, 6, 1),
            date(2026, 6, 2),
            date(2026, 6, 20),
        ]

    def test_trims_comments_from_notes_cleaning(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
                notes="nota de reserva",
                notes_cleaning="  dejar llaves en conserjería  ",
            )
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert opportunities[0].comments == "dejar llaves en conserjería"

    def test_comments_come_from_the_arriving_booking(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
                notes_cleaning="notas de quien se va",
            ),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 6, 10),
                check_out=date(2026, 6, 15),
                notes_cleaning="notas de quien llega",
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        # La limpieza la identifica la reserva que llega: sus notas son las que se ven y editan.
        assert opportunities[1].source_booking_record_id == 2
        assert opportunities[1].comments == "notas de quien llega"

    def test_empty_comments_when_notes_cleaning_are_none(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
                notes="nota de reserva",
                notes_cleaning=None,
            )
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert opportunities[0].comments == ""

    def test_ignores_booking_notes_for_cleaning_comments(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
                notes="solo notas de reserva",
                notes_cleaning=None,
            )
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert opportunities[0].comments == ""

    def test_uses_standard_times_when_bookings_do_not_set_them(self):
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
                check_in=date(2026, 6, 8),
                check_out=date(2026, 6, 12),
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        assert opportunities[1].available_from_time == time(11, 0)
        assert opportunities[1].available_until_time == time(16, 0)

    def test_uses_times_agreed_on_each_booking(self):
        bookings = [
            make_booking(
                record_id=1,
                apartment_id="R180",
                check_in=date(2026, 6, 1),
                check_out=date(2026, 6, 5),
                check_out_time=time(13, 30),
            ),
            make_booking(
                record_id=2,
                apartment_id="R180",
                check_in=date(2026, 6, 8),
                check_out=date(2026, 6, 12),
                check_in_time=time(18, 0),
            ),
        ]

        opportunities = _build_cleaning_opportunities(bookings)

        # La hora de salida sale de la reserva que se va y la de entrada de la que llega.
        assert opportunities[1].available_from_time == time(13, 30)
        assert opportunities[1].available_until_time == time(18, 0)
        assert opportunities[1].previous_booking_record_id == 1


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

    def test_excludes_window_entirely_before_range(self):
        assert not _cleaning_window_overlaps_range(
            date(2026, 5, 1),
            date(2026, 5, 10),
            date(2026, 6, 15),
            date(2026, 7, 12),
        )

    def test_excludes_window_entirely_after_range(self):
        assert not _cleaning_window_overlaps_range(
            date(2026, 7, 20),
            date(2026, 7, 25),
            date(2026, 6, 15),
            date(2026, 7, 12),
        )


class TestGetCleaningOpportunitiesUseCase:
    def test_delegates_to_repository_with_operational_date_range(self, mock_repo):
        mock_repo.search_bookings.return_value = []
        use_case = GetCleaningOpportunitiesUseCase(mock_repo)
        reference_date = date(2026, 6, 18)

        assert use_case.execute(reference_date=reference_date) == []
        mock_repo.search_bookings.assert_called_once_with(
            start_date=date(2026, 5, 18),
            end_date=date(2026, 10, 10),
        )

    def test_week_start_anchors_range_on_a_past_week(self, mock_repo):
        mock_repo.search_bookings.return_value = []
        use_case = GetCleaningOpportunitiesUseCase(mock_repo)

        assert use_case.execute(reference_date=date(2026, 6, 18), week_start=date(2026, 3, 4)) == []
        # El rango arranca el lunes de la semana pedida, no el de la semana de hoy.
        mock_repo.search_bookings.assert_called_once_with(
            start_date=date(2026, 2, 2),
            end_date=date(2026, 6, 27),
        )

    def test_week_start_does_not_shift_the_instant_used_for_can_bill(self, mock_repo):
        # Ventana ya limpiable "ahora"; mirar una semana pasada no debe cambiarlo.
        mock_repo.search_bookings.return_value = [
            make_booking(
                record_id=1,
                apartment_id="R106",
                check_in=date(2026, 3, 2),
                check_out=date(2026, 3, 5),
            ),
        ]
        use_case = GetCleaningOpportunitiesUseCase(mock_repo)

        opportunities = use_case.execute_at(
            reference_datetime=datetime(2026, 6, 18, 12, 0),
            week_start=date(2026, 3, 2),
        )

        window = next(o for o in opportunities if o.source_booking_record_id == 1)
        assert window.can_bill is True

    def test_populates_apartment_address_from_repository(self, mock_repo):
        mock_repo.search_bookings.return_value = [
            make_booking(
                record_id=1,
                apartment_id="R106",
                check_in=date(2026, 6, 15),
                check_out=date(2026, 6, 19),
            ),
        ]

        class _ApartmentRepo:
            def get_all(self):
                return [
                    make_apartment(
                        apartment_id="R106",
                        address="C/ Raquero 6 Bloque 3",
                        apartment_description="Porto Fino",
                    )
                ]

        use_case = GetCleaningOpportunitiesUseCase(mock_repo, apartment_repository=_ApartmentRepo())

        opportunities = use_case.execute(reference_date=date(2026, 6, 18))

        window = next(o for o in opportunities if o.source_booking_record_id == 1)
        assert window.address == "C/ Raquero 6 Bloque 3"
        assert window.apartment_description == "Porto Fino"

    def test_excludes_windows_outside_operational_range(self, mock_repo):
        mock_repo.search_bookings.return_value = [
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

    def test_window_uses_checkout_when_previous_is_in_same_week_as_checkin(self):
        """Si el check-out anterior está en la misma semana que el check-in,
        el available_from apunta al check-out, y la ventana es visible."""
        # range_start = lun 2026-06-15, range_end = dom 2026-07-12
        # El rango de fetch es: start = 2026-05-18, end = 2026-10-10

        class _FilteringRepo:
            def __init__(self, bookings):
                self._bookings = bookings

            def search_bookings(self, start_date=None, end_date=None, **_):
                return [
                    b
                    for b in self._bookings
                    if b.check_in <= end_date and b.check_out >= start_date
                ]

        # Check-out viernes 2026-06-19, check-in lunes 2026-06-22 (misma semana: lun15-dom21)
        previous = make_booking(
            record_id=1,
            apartment_id="R180",
            check_in=date(2026, 6, 15),
            check_out=date(2026, 6, 19),
        )
        arriving = make_booking(
            record_id=2,
            apartment_id="R180",
            check_in=date(2026, 6, 22),
            check_out=date(2026, 6, 25),
        )
        use_case = GetCleaningOpportunitiesUseCase(_FilteringRepo([previous, arriving]))

        opportunities = use_case.execute(reference_date=date(2026, 6, 18))

        window = next(o for o in opportunities if o.source_booking_record_id == 2)
        assert window.available_from == date(2026, 6, 19)
        assert window.available_until == date(2026, 6, 22)
        assert window.previous_booking_record_id == 1
