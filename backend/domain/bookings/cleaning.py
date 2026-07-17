"""
Regla de dominio de las limpiezas.

Se limpia para preparar una entrada: existe una limpieza por cada check-in, haya o no
check-out previo. La ventana la cierra el check-in de la reserva y la abre la salida de la
reserva anterior del mismo apartamento; si no hay reserva anterior, no hay salida que
esperar y la ventana se abre el lunes de la semana del check-in.
"""

from datetime import datetime, timedelta

from domain.bookings.entity import DEFAULT_CHECKOUT_TIME, Booking


def _cleaning_sort_key(booking: Booking) -> tuple[object, ...]:
    return (booking.check_in, booking.check_out, booking.record_id or 0)


def sort_for_cleaning(bookings: list[Booking]) -> list[Booking]:
    """Reservas que cuentan para las limpiezas, en orden cronológico.

    Se descartan las canceladas (no ocupan el piso, así que no hay nada que preparar) y las
    aún no persistidas (sin ``record_id`` no se pueden facturar ni comentar).
    """
    return sorted(
        (
            booking
            for booking in bookings
            if not booking.is_cancelled() and booking.record_id is not None
        ),
        key=_cleaning_sort_key,
    )


def find_previous_booking(booking: Booking, apartment_bookings: list[Booking]) -> Booking | None:
    """Reserva inmediatamente anterior a *booking* en su apartamento; None si es la primera.

    *apartment_bookings* debe contener las reservas del apartamento de *booking*; se ordenan
    y filtran aquí, así que puede pasarse tal cual venga del repositorio.
    """
    key = _cleaning_sort_key(booking)
    earlier = [
        candidate
        for candidate in sort_for_cleaning(apartment_bookings)
        if _cleaning_sort_key(candidate) < key
    ]
    return earlier[-1] if earlier else None


def cleaning_window_start(booking: Booking, previous: Booking | None) -> datetime:
    """Instante a partir del cual se puede limpiar para preparar la entrada de *booking*.

    Con reserva anterior, la ventana la abre su salida real. Sin ella, el piso ya está libre:
    se abre el lunes de la semana del check-in, a la hora estándar de salida.
    """
    if previous is not None:
        return previous.cleaning_available_at()

    monday = booking.check_in - timedelta(days=booking.check_in.weekday())
    return datetime.combine(monday, DEFAULT_CHECKOUT_TIME)
