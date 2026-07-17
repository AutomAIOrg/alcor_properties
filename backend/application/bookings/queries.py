"""
Casos de uso de lectura (consultas) para el dominio de Reservas.
"""

from datetime import date, datetime, timedelta
from typing import Any

from application.bookings.helpers import (
    ElectricRates,
    apply_all,
    apply_electric_allowance,
    compute_stats,
    count_days_without_bookings,
)
from domain.apartments.entity import Apartment
from domain.apartments.repository import IApartmentRepository
from domain.bills.repository import IBillRepository
from domain.bookings.cleaning import cleaning_window_start, sort_for_cleaning
from domain.bookings.entity import Booking, CleaningOpportunity
from domain.bookings.repository import IBookingRepository

_CLEANING_OPERATIONAL_WEEKS = 4
# Margen hacia atrás para encontrar la reserva anterior, que es la que abre la ventana. Si su
# estancia terminó antes de este margen, la limpieza degrada a ventana de cabecera (lunes de
# la semana del check-in): tras semanas de piso vacío, esa es la información útil.
_CLEANING_BOOKING_LOOKBACK_DAYS = 28
# Margen hacia delante para traer la reserva que llega. Es la que ancla la limpieza, así que
# sin ella la ventana no existe: este margen decide hasta dónde se ven limpiezas futuras.
_CLEANING_BOOKING_LOOKAHEAD_DAYS = 90


def _cleaning_operational_range(reference_date: date | None = None) -> tuple[date, date]:
    """Devuelve el lunes de la semana de referencia y el domingo de las 3 semanas siguientes."""
    today = reference_date or date.today()
    range_start = today - timedelta(days=today.weekday())
    range_end = range_start + timedelta(days=_CLEANING_OPERATIONAL_WEEKS * 7 - 1)
    return range_start, range_end


def _cleaning_window_overlaps_range(
    available_from: date,
    available_until: date,
    range_start: date,
    range_end: date,
) -> bool:
    """True si la ventana es relevante dentro del rango operativo de limpiezas."""
    return available_from <= range_end and available_until >= range_start


class ListBookingsQuery:
    """
    Devuelve reservas con filtrado opcional por fechas y límite de resultados.

    Tres modos de llamada (coinciden con el endpoint GET /bookings/ existente):
    - start_date + end_date  → reservas que se superponen con ese rango
    - start_date + days      → reservas a partir de start_date durante N días
    - (ninguno)              → todas las reservas, opcionalmente limitadas por cantidad
    """

    def __init__(
        self,
        repository: IBookingRepository,
        electric_rates: ElectricRates,
    ) -> None:
        self._repo = repository
        self._electric_rates = electric_rates

    def execute(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int | None = None,
        limit: int | None = None,
        apartment_id: str | None = None,
        status: str | None = None,
        guest_name: str | None = None,
        booking_number: str | None = None,
        search: str | None = None,
    ) -> list[Booking]:
        if start_date and end_date:
            bookings = self._repo.search_bookings(
                start_date=start_date,
                end_date=end_date,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
                search=search,
            )
        elif days is not None:
            resolved_start = start_date or date.today()
            resolved_end = resolved_start + timedelta(days=days)
            bookings = self._repo.search_bookings(
                start_date=resolved_start,
                end_date=resolved_end,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
                search=search,
            )
        elif start_date or end_date:
            bookings = self._repo.search_bookings(
                start_date=start_date,
                end_date=end_date,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
                search=search,
            )
        else:
            bookings = self._repo.search_bookings(
                limit=limit,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
                search=search,
            )
        return apply_all(bookings, self._electric_rates)


class GetBookingStatsQuery:
    """
    Calcula estadísticas agregadas sobre reservas aplicando los mismos filtros que ListBookingsQuery.
    """

    def __init__(
        self,
        repository: IBookingRepository,
        electric_rates: ElectricRates,
    ) -> None:
        self._repo = repository
        self._electric_rates = electric_rates

    def execute(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        days: int | None = None,
        apartment_id: str | None = None,
        status: str | None = None,
        guest_name: str | None = None,
        booking_number: str | None = None,
    ) -> dict:
        range_start: date | None = None
        range_end: date | None = None

        if start_date and end_date:
            range_start = start_date
            range_end = end_date
            bookings = self._repo.search_bookings(
                start_date=range_start,
                end_date=range_end,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )
        elif days is not None:
            range_start = start_date or date.today()
            range_end = range_start + timedelta(days=days)
            bookings = self._repo.search_bookings(
                start_date=range_start,
                end_date=range_end,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )
        elif start_date or end_date:
            range_start = start_date
            range_end = end_date
            bookings = self._repo.search_bookings(
                start_date=range_start,
                end_date=range_end,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )
        else:
            bookings = self._repo.search_bookings(
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )

        bookings = apply_all(bookings, self._electric_rates)

        occupancy_pct = None
        no_booking_days_pct = None
        if range_start and range_end:
            range_days = (range_end - range_start).days
            if range_days > 0:
                days_without_bookings = count_days_without_bookings(
                    bookings, range_start, range_end
                )
                no_booking_days_pct = round(days_without_bookings / range_days * 100, 2)
                occupancy_pct = round((range_days - days_without_bookings) / range_days * 100, 2)

        return compute_stats(
            bookings,
            start_date=range_start,
            end_date=range_end,
            occupancy_pct=occupancy_pct,
            no_booking_days_pct=no_booking_days_pct,
        )


class GetBookingByIdQuery:
    """Devuelve una sola reserva por su ID en la base de datos."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_rates: ElectricRates,
    ) -> None:
        self._repo = repository
        self._electric_rates = electric_rates

    def execute(self, record_id: int) -> Booking:
        booking = self._repo.get_by_id(record_id)  # lanza BookingNotFound si no existe
        return apply_electric_allowance(booking, self._electric_rates)


class GetActiveBookingsQuery:
    """Devuelve reservas donde los huéspedes están actualmente alojados (check_in <= hoy < check_out)."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_rates: ElectricRates,
    ) -> None:
        self._repo = repository
        self._electric_rates = electric_rates

    def execute(self) -> list[Booking]:
        today = date.today()
        bookings = self._repo.search_bookings(start_date=today, end_date=today + timedelta(days=1))
        active = [b for b in bookings if b.is_active()]
        return apply_all(active, self._electric_rates)


class GetUpcomingCheckinsQuery:
    """Devuelve reservas cuyo check-in cae dentro de los próximos N días, ordenadas por fecha."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_rates: ElectricRates,
    ) -> None:
        self._repo = repository
        self._electric_rates = electric_rates

    def execute(self, days: int = 7) -> list[Booking]:
        today = date.today()
        end_date = today + timedelta(days=days)
        bookings = self._repo.search_bookings(
            start_date=today, end_date=end_date + timedelta(days=1)
        )
        upcoming = [b for b in bookings if b.has_upcoming_checkin(days)]
        upcoming.sort(key=lambda b: b.check_in)
        return apply_all(upcoming, self._electric_rates)


class GetUpcomingCheckoutsQuery:
    """Devuelve reservas cuyo check-out cae dentro de los próximos N días, ordenadas por fecha."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_rates: ElectricRates,
    ) -> None:
        self._repo = repository
        self._electric_rates = electric_rates

    def execute(self, days: int = 7) -> list[Booking]:
        today = date.today()
        end_date = today + timedelta(days=days)
        bookings = self._repo.search_bookings(
            start_date=today - timedelta(days=1),
            end_date=end_date + timedelta(days=1),
        )
        upcoming = [b for b in bookings if b.has_upcoming_checkout(days)]
        upcoming.sort(key=lambda b: b.check_out)
        return apply_all(upcoming, self._electric_rates)


class GetCalendarEventsQuery:
    """
    Devuelve reservas formateadas como diccionarios de eventos de calendario para un periodo dado.

    Se excluyen las reservas canceladas cuyo check-in sea dentro de 3 días.
    """

    def __init__(
        self,
        repository: IBookingRepository,
        electric_rates: ElectricRates,
    ) -> None:
        self._repo = repository
        self._electric_rates = electric_rates

    def execute(
        self,
        start_date: date | None = None,
        days: int = 90,
    ) -> list[dict[str, Any]]:
        resolved_start = start_date or date.today()
        end_date = resolved_start + timedelta(days=days)
        bookings = self._repo.search_bookings(start_date=resolved_start, end_date=end_date)
        bookings = apply_all(bookings, self._electric_rates)

        today = date.today()
        events = []
        for booking in bookings:
            if booking.is_cancelled() and (booking.check_in - today).days < 3:
                continue
            events.append(
                {
                    "id": f"booking-{booking.record_id}",
                    "title": f"{booking.apartment_id} - {booking.guest_name}",
                    "start": booking.check_in.isoformat(),
                    "end": booking.check_out.isoformat(),
                    "allDay": True,
                    "classNames": ["reserva"] + (["cancelled"] if booking.is_cancelled() else []),
                    "extendedProps": {
                        "record_id": booking.record_id,
                        "apartment_id": booking.apartment_id,
                        "booking_number": booking.booking_number,
                        "guest_name": booking.guest_name,
                        "check_in": booking.check_in.isoformat(),
                        "check_out": booking.check_out.isoformat(),
                        "status": booking.status,
                        "nights": booking.nights,
                        "persons": booking.persons,
                        "adults": booking.adults,
                        "children": booking.children,
                        "email": booking.email,
                        "phone": booking.phone,
                        "price": booking.price,
                        "charges": booking.charges,
                        "electric_allowance": booking.electric_allowance,
                        "source": "database",
                    },
                }
            )
        return events


def _build_cleaning_opportunities(
    bookings: list[Booking],
    billed_booking_ids: set[int] | None = None,
    reference_datetime: datetime | None = None,
    bill_states_by_booking: dict[int, str] | None = None,
    apartments_by_id: dict[str, Apartment] | None = None,
) -> list[CleaningOpportunity]:
    """Calcula una limpieza por cada check-in: solo se limpia para preparar una entrada.

    La ventana la cierra el check-in de la reserva y la abre la salida de la reserva anterior
    del mismo apartamento; si no hay reserva anterior, el lunes de la semana del check-in.
    """
    billed = billed_booking_ids or set()
    bill_states = bill_states_by_booking or {}
    apartments = apartments_by_id or {}
    now = reference_datetime or datetime.now()

    by_apartment: dict[str, list[Booking]] = {}
    for booking in sort_for_cleaning(bookings):
        by_apartment.setdefault(booking.apartment_id, []).append(booking)

    opportunities: list[CleaningOpportunity] = []
    for apartment_bookings in by_apartment.values():
        for index, booking in enumerate(apartment_bookings):
            assert booking.record_id is not None  # sort_for_cleaning ya descarta las sin ID

            previous = apartment_bookings[index - 1] if index else None
            window_start = cleaning_window_start(booking, previous)
            apartment = apartments.get(booking.apartment_id)
            opportunities.append(
                CleaningOpportunity(
                    source_booking_record_id=booking.record_id,
                    apartment_id=booking.apartment_id,
                    available_from=window_start.date(),
                    available_until=booking.check_in,
                    available_from_time=window_start.time(),
                    available_until_time=booking.effective_check_in_time(),
                    comments=(booking.notes_cleaning or "").strip(),
                    has_bill=booking.record_id in billed,
                    can_bill=now >= window_start,
                    bill_state=bill_states.get(booking.record_id),
                    address=apartment.address if apartment else None,
                    apartment_description=(apartment.apartment_description if apartment else None),
                    previous_booking_record_id=previous.record_id if previous else None,
                    persons=booking.persons,
                    nights=booking.nights,
                )
            )

    opportunities.sort(
        key=lambda opportunity: (
            opportunity.available_until,
            opportunity.available_from,
            opportunity.apartment_id,
        )
    )
    return opportunities


class GetCleaningOpportunitiesUseCase:
    """Obtiene ventanas de limpieza del rango operativo (semana actual + 3 siguientes)."""

    def __init__(
        self,
        repository: IBookingRepository,
        bill_repository: IBillRepository | None = None,
        apartment_repository: IApartmentRepository | None = None,
    ) -> None:
        self._repo = repository
        self._bills = bill_repository
        self._apartments = apartment_repository

    def execute(
        self,
        reference_date: date | None = None,
        week_start: date | None = None,
    ) -> list[CleaningOpportunity]:
        reference_datetime = (
            datetime.combine(reference_date, datetime.min.time()) if reference_date else None
        )
        return self.execute_at(reference_datetime, week_start=week_start)

    def execute_at(
        self,
        reference_datetime: datetime | None = None,
        week_start: date | None = None,
    ) -> list[CleaningOpportunity]:
        """Igual que :meth:`execute` pero con un instante exacto (para calcular ``can_bill``).

        ``week_start`` ancla el rango operativo en otra semana (cualquiera, también
        pasada) sin alterar el instante con el que se calcula ``can_bill``.
        """
        now = reference_datetime or datetime.now()
        range_start, range_end = _cleaning_operational_range(week_start or now.date())
        bookings = self._repo.search_bookings(
            start_date=range_start - timedelta(days=_CLEANING_BOOKING_LOOKBACK_DAYS),
            end_date=range_end + timedelta(days=_CLEANING_BOOKING_LOOKAHEAD_DAYS),
        )
        billed_ids = self._bills.list_billed_booking_ids() if self._bills else set()
        bill_states = self._bills.get_bill_states_by_booking() if self._bills else {}
        apartments_by_id = (
            {apartment.apartment_id: apartment for apartment in self._apartments.get_all()}
            if self._apartments
            else {}
        )
        opportunities = _build_cleaning_opportunities(
            bookings,
            billed_ids,
            reference_datetime=now,
            bill_states_by_booking=bill_states,
            apartments_by_id=apartments_by_id,
        )
        return [
            opportunity
            for opportunity in opportunities
            if _cleaning_window_overlaps_range(
                opportunity.available_from,
                opportunity.available_until,
                range_start,
                range_end,
            )
        ]
