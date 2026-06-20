"""
Funciones auxiliares compartidas entre queries y commands del dominio de Reservas.
"""

from datetime import date, timedelta

from domain.bookings.entity import Booking


def apply_electric_allowance(booking: Booking, electric_ids: set[str]) -> Booking:
    """Establece electric_allowance en una reserva según los IDs configurados."""
    if booking.apartment_id.strip() in electric_ids:
        booking.electric_allowance = booking.nights * 4.0
    else:
        booking.electric_allowance = None
    return booking


def apply_all(bookings: list[Booking], electric_ids: set[str]) -> list[Booking]:
    return [apply_electric_allowance(b, electric_ids) for b in bookings]


def booking_overlap_nights(booking: Booking, start_date: date, end_date: date) -> int:
    return max((min(booking.check_out, end_date) - max(booking.check_in, start_date)).days, 0)


def count_days_without_bookings(
    bookings: list[Booking],
    start_date: date,
    end_date: date,
) -> int:
    """Cuenta los dias del rango semiabierto [start_date, end_date) sin ninguna reserva activa."""
    booked_days: set[date] = set()
    for booking in bookings:
        if booking.is_cancelled():
            continue

        current = max(booking.check_in, start_date)
        last = min(booking.check_out, end_date)
        while current < last:
            booked_days.add(current)
            current += timedelta(days=1)

    return (end_date - start_date).days - len(booked_days)


def compute_stats(
    bookings: list[Booking],
    start_date: date | None = None,
    end_date: date | None = None,
    occupancy_pct: float | None = None,
    no_booking_days_pct: float | None = None,
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
        round(total_revenue / len(prices), 2)
        if total_revenue is not None and len(prices) > 0
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
        "no_booking_days_pct": no_booking_days_pct,
    }
