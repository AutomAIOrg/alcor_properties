"""
Casos de uso de lectura (consultas) para el dominio de Reservas.
"""

from datetime import date, timedelta
from typing import Any

from domain.bookings.entity import Booking
from domain.bookings.repository import IBookingRepository


def _apply_electric_allowance(booking: Booking, electric_ids: set[str]) -> Booking:
    """Establece electric_allowance en una reserva según los IDs configurados."""
    if booking.apartment_id.strip() in electric_ids:
        booking.electric_allowance = booking.nights * 4.0
    else:
        booking.electric_allowance = None
    return booking


def _apply_all(bookings: list[Booking], electric_ids: set[str]) -> list[Booking]:
    return [_apply_electric_allowance(b, electric_ids) for b in bookings]


def _booking_overlap_nights(booking: Booking, start_date: date, end_date: date) -> int:
    return max((min(booking.check_out, end_date) - max(booking.check_in, start_date)).days, 0)


def _sum_occupied_nights(
    bookings: list[Booking],
    start_date: date,
    end_date: date,
) -> int:
    """Suma solo las noches ocupadas dentro del rango semiabierto [start_date, end_date)."""
    return sum(
        _booking_overlap_nights(booking, start_date, end_date)
        for booking in bookings
        if not booking.is_cancelled()
    )


def _compute_stats(
    bookings: list[Booking],
    start_date: date | None = None,
    end_date: date | None = None,
    occupancy_pct: float | None = None,
) -> dict:
    """
    Calcula estadísticas agregadas a partir de una lista de reservas.

    Las métricas financieras y de noches excluyen reservas canceladas.
    El parámetro occupancy_pct se calcula externamente y se inyecta aquí.
    """
    total = len(bookings)
    cancelled = [b for b in bookings if b.status.lower() == "cancelled"]
    active = [b for b in bookings if b.status.lower() != "cancelled"]

    cancelled_count = len(cancelled)
    active_count = len(active)
    cancellation_rate = round(cancelled_count / total * 100, 2) if total > 0 else None

    total_nights = sum(b.nights for b in active)
    avg_nights = round(total_nights / active_count, 2) if active_count > 0 else None

    total_persons = sum(b.persons for b in active)
    avg_persons = round(total_persons / active_count, 2) if active_count > 0 else None

    prices = [float(b.price) for b in active if b.price is not None]
    total_revenue = round(sum(prices), 2) if prices else None
    avg_rev_booking = (
        round(total_revenue / active_count, 2)
        if total_revenue is not None and active_count > 0
        else None
    )
    avg_rev_night = (
        round(total_revenue / total_nights, 2)
        if total_revenue is not None and total_nights > 0
        else None
    )

    charges = [float(b.charges) for b in active if b.charges is not None]
    total_charges = round(sum(charges), 2) if charges else None

    electric = [float(b.electric_allowance) for b in active if b.electric_allowance is not None]
    total_electric = round(sum(electric), 2) if electric else None

    status_breakdown: dict[str, int] = {}
    for b in bookings:
        key = b.status if b.status else "Unknown"
        status_breakdown[key] = status_breakdown.get(key, 0) + 1

    return {
        "total_bookings": total,
        "active_bookings": active_count,
        "cancelled_bookings": cancelled_count,
        "cancellation_rate": cancellation_rate,
        "total_nights": total_nights,
        "avg_nights_per_booking": avg_nights,
        "total_persons": total_persons,
        "avg_persons_per_booking": avg_persons,
        "total_revenue": total_revenue,
        "avg_revenue_per_booking": avg_rev_booking,
        "avg_revenue_per_night": avg_rev_night,
        "total_charges": total_charges,
        "total_electric_allowance": total_electric,
        "status_breakdown": status_breakdown,
        "start_date": start_date,
        "end_date": end_date,
        "occupancy_pct": occupancy_pct,
    }


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
        return _apply_all(bookings, self._electric_ids)


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

        bookings = _apply_all(bookings, self._electric_ids)

        occupancy_pct = None
        if range_start and range_end:
            range_days = (range_end - range_start).days
            if range_days > 0:
                occupied_nights = _sum_occupied_nights(bookings, range_start, range_end)
                occupancy_pct = round(occupied_nights / range_days * 100, 2)

        return _compute_stats(
            bookings, start_date=range_start, end_date=range_end, occupancy_pct=occupancy_pct
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
        return _apply_electric_allowance(booking, self._electric_ids)


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
        bookings = self._repo.list(start_date=today, end_date=end_date + timedelta(days=1))
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
        bookings = self._repo.list(
            start_date=today - timedelta(days=1),
            end_date=end_date + timedelta(days=1),
        )
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
