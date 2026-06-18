"""
Casos de uso de lectura (consultas) para el dominio de Reservas.
"""

from datetime import date, timedelta
from typing import Any

from domain.bookings.entity import Booking, CleaningOpportunity
from domain.bookings.repository import IBookingRepository

_CLEANING_OPERATIONAL_WEEKS = 4
_CLEANING_BOOKING_LOOKBACK_DAYS = 28


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


def _apply_electric_allowance(booking: Booking, electric_ids: set[str]) -> Booking:
    """Establece electric_allowance en una reserva según los IDs configurados."""
    if booking.apartment_id.strip() in electric_ids:
        booking.electric_allowance = booking.nights * 4.0
    else:
        booking.electric_allowance = None
    return booking


def _apply_all(bookings: list[Booking], electric_ids: set[str]) -> list[Booking]:
    return [_apply_electric_allowance(b, electric_ids) for b in bookings]


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
    ) -> list[Booking]:
        if start_date and end_date:
            bookings = self._repo.list(start_date=start_date, end_date=end_date)
        elif days is not None:
            resolved_start = start_date or date.today()
            resolved_end = resolved_start + timedelta(days=days)
            bookings = self._repo.list(start_date=resolved_start, end_date=resolved_end)
        else:
            bookings = self._repo.list(limit=limit)
        return _apply_all(bookings, self._electric_ids)


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
        return _apply_electric_allowance(booking, self._electric_ids)


class GetActiveBookingsQuery:
    """Devuelve reservas donde los huéspedes están actualmente alojados (check_in <= hoy <= check_out)."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

    def execute(self) -> list[Booking]:
        today = date.today()
        bookings = self._repo.list(start_date=today, end_date=today)
        active = [b for b in bookings if b.is_active()]
        return _apply_all(active, self._electric_ids)


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
        bookings = self._repo.list(start_date=today, end_date=end_date)
        upcoming = [b for b in bookings if b.has_upcoming_checkin(days)]
        upcoming.sort(key=lambda b: b.check_in)
        return _apply_all(upcoming, self._electric_ids)


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
        bookings = self._repo.list(start_date=today, end_date=end_date)
        upcoming = [b for b in bookings if b.has_upcoming_checkout(days)]
        upcoming.sort(key=lambda b: b.check_out)
        return _apply_all(upcoming, self._electric_ids)


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
        bookings = _apply_all(bookings, self._electric_ids)

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


def _build_cleaning_opportunities(bookings: list[Booking]) -> list[CleaningOpportunity]:
    """Calcula ventanas de limpieza a partir de reservas activas agrupadas por apartamento."""
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
            opportunities.append(
                CleaningOpportunity(
                    source_booking_record_id=booking.record_id,
                    apartment_id=booking.apartment_id,
                    available_from=booking.check_out,
                    available_until=next_booking.check_in if next_booking else None,
                    comments=(booking.notes or "").strip(),
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

    def __init__(self, repository: IBookingRepository) -> None:
        self._repo = repository

    def execute(self, reference_date: date | None = None) -> list[CleaningOpportunity]:
        range_start, range_end = _cleaning_operational_range(reference_date)
        bookings = self._repo.list(
            start_date=range_start - timedelta(days=_CLEANING_BOOKING_LOOKBACK_DAYS),
            end_date=range_end,
        )
        opportunities = _build_cleaning_opportunities(bookings)
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
