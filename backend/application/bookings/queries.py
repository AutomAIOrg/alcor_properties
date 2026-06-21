"""
Casos de uso de lectura (consultas) para el dominio de Reservas.
"""

from datetime import date, datetime, timedelta
from typing import Any

from application.bookings.helpers import (
    apply_all,
    apply_electric_allowance,
    compute_stats,
    count_days_without_bookings,
)
from domain.bills.repository import IBillRepository
from domain.bookings.entity import Booking, CleaningOpportunity
from domain.bookings.repository import IBookingRepository

_CLEANING_OPERATIONAL_WEEKS = 4
_CLEANING_BOOKING_LOOKBACK_DAYS = 28
# Margen hacia delante para detectar la siguiente reserva (y así calcular available_until)
# aunque su check-in caiga después del rango operativo.
_CLEANING_BOOKING_LOOKAHEAD_DAYS = 90


def _cleaning_operational_range(reference_date: date | None = None) -> tuple[date, date]:
    """Devuelve el lunes de la semana de referencia y el domingo de las 3 semanas siguientes."""
    today = reference_date or date.today()
    range_start = today - timedelta(days=today.weekday())
    range_end = range_start + timedelta(days=_CLEANING_OPERATIONAL_WEEKS * 7 - 1)
    return range_start, range_end


def _cleaning_window_overlaps_range(
    available_from: date,
    available_until: date | None,
    range_start: date,
    range_end: date,
) -> bool:
    """True si la ventana es relevante dentro del rango operativo de limpiezas."""
    if available_until is None:
        return range_start <= available_from <= range_end
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
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

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
    ) -> list[Booking]:
        if start_date and end_date:
            bookings = self._repo.list(
                start_date=start_date,
                end_date=end_date,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )
        elif days is not None:
            resolved_start = start_date or date.today()
            resolved_end = resolved_start + timedelta(days=days)
            bookings = self._repo.list(
                start_date=resolved_start,
                end_date=resolved_end,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )
        elif start_date or end_date:
            bookings = self._repo.list(
                start_date=start_date,
                end_date=end_date,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )
        else:
            bookings = self._repo.list(
                limit=limit,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )
        return apply_all(bookings, self._electric_ids)


class GetBookingStatsQuery:
    """
    Calcula estadísticas agregadas sobre reservas aplicando los mismos filtros que ListBookingsQuery.
    """

    def __init__(
        self,
        repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

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
            bookings = self._repo.list(
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
            bookings = self._repo.list(
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
            bookings = self._repo.list(
                start_date=range_start,
                end_date=range_end,
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )
        else:
            bookings = self._repo.list(
                apartment_id=apartment_id,
                status=status,
                guest_name=guest_name,
                booking_number=booking_number,
            )

        bookings = apply_all(bookings, self._electric_ids)

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
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

    def execute(self, record_id: int) -> Booking:
        booking = self._repo.get_by_id(record_id)  # lanza BookingNotFound si no existe
        return apply_electric_allowance(booking, self._electric_ids)


class GetActiveBookingsQuery:
    """Devuelve reservas donde los huéspedes están actualmente alojados (check_in <= hoy < check_out)."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

    def execute(self) -> list[Booking]:
        today = date.today()
        bookings = self._repo.list(start_date=today, end_date=today + timedelta(days=1))
        active = [b for b in bookings if b.is_active()]
        return apply_all(active, self._electric_ids)


class GetUpcomingCheckinsQuery:
    """Devuelve reservas cuyo check-in cae dentro de los próximos N días, ordenadas por fecha."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

    def execute(self, days: int = 7) -> list[Booking]:
        today = date.today()
        end_date = today + timedelta(days=days)
        bookings = self._repo.list(start_date=today, end_date=end_date + timedelta(days=1))
        upcoming = [b for b in bookings if b.has_upcoming_checkin(days)]
        upcoming.sort(key=lambda b: b.check_in)
        return apply_all(upcoming, self._electric_ids)


class GetUpcomingCheckoutsQuery:
    """Devuelve reservas cuyo check-out cae dentro de los próximos N días, ordenadas por fecha."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

    def execute(self, days: int = 7) -> list[Booking]:
        today = date.today()
        end_date = today + timedelta(days=days)
        bookings = self._repo.list(
            start_date=today - timedelta(days=1),
            end_date=end_date + timedelta(days=1),
        )
        upcoming = [b for b in bookings if b.has_upcoming_checkout(days)]
        upcoming.sort(key=lambda b: b.check_out)
        return apply_all(upcoming, self._electric_ids)


class GetCalendarEventsQuery:
    """
    Devuelve reservas formateadas como diccionarios de eventos de calendario para un periodo dado.

    Se excluyen las reservas canceladas cuyo check-in sea dentro de 3 días.
    """

    def __init__(
        self,
        repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

    def execute(
        self,
        start_date: date | None = None,
        days: int = 90,
    ) -> list[dict[str, Any]]:
        resolved_start = start_date or date.today()
        end_date = resolved_start + timedelta(days=days)
        bookings = self._repo.list(start_date=resolved_start, end_date=end_date)
        bookings = apply_all(bookings, self._electric_ids)

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
) -> list[CleaningOpportunity]:
    """Calcula ventanas de limpieza a partir de reservas activas agrupadas por apartamento."""
    billed = billed_booking_ids or set()
    bill_states = bill_states_by_booking or {}
    now = reference_datetime or datetime.now()
    active_bookings = [
        booking
        for booking in bookings
        if not booking.is_cancelled() and booking.record_id is not None
    ]

    by_apartment: dict[str, list[Booking]] = {}
    for booking in active_bookings:
        by_apartment.setdefault(booking.apartment_id, []).append(booking)

    opportunities: list[CleaningOpportunity] = []
    for apartment_bookings in by_apartment.values():
        apartment_bookings.sort(key=lambda b: (b.check_in, b.check_out, b.record_id))
        for index, booking in enumerate(apartment_bookings):
            if booking.record_id is None:
                continue

            next_booking = (
                apartment_bookings[index + 1] if index + 1 < len(apartment_bookings) else None
            )
            bill_st = bill_states.get(booking.record_id)
            opportunities.append(
                CleaningOpportunity(
                    source_booking_record_id=booking.record_id,
                    apartment_id=booking.apartment_id,
                    available_from=booking.check_out,
                    available_until=next_booking.check_in if next_booking else None,
                    comments=(booking.notes or "").strip(),
                    has_bill=booking.record_id in billed,
                    can_bill=booking.is_cleanable(now),
                    bill_state=bill_st,
                )
            )

    opportunities.sort(
        key=lambda opportunity: (
            opportunity.available_until is None,
            opportunity.available_until or date.min,
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
    ) -> None:
        self._repo = repository
        self._bills = bill_repository

    def execute(self, reference_date: date | None = None) -> list[CleaningOpportunity]:
        reference_datetime = (
            datetime.combine(reference_date, datetime.min.time()) if reference_date else None
        )
        return self.execute_at(reference_datetime)

    def execute_at(self, reference_datetime: datetime | None = None) -> list[CleaningOpportunity]:
        """Igual que :meth:`execute` pero con un instante exacto (para calcular ``can_bill``)."""
        now = reference_datetime or datetime.now()
        range_start, range_end = _cleaning_operational_range(now.date())
        bookings = self._repo.list(
            start_date=range_start - timedelta(days=_CLEANING_BOOKING_LOOKBACK_DAYS),
            end_date=range_end + timedelta(days=_CLEANING_BOOKING_LOOKAHEAD_DAYS),
        )
        billed_ids = self._bills.list_billed_booking_ids() if self._bills else set()
        bill_states = self._bills.get_bill_states_by_booking() if self._bills else {}
        opportunities = _build_cleaning_opportunities(
            bookings, billed_ids, reference_datetime=now, bill_states_by_booking=bill_states
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
