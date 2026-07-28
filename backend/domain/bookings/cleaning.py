"""
Regla de dominio de las limpiezas.

Se limpia para preparar una entrada: existe una limpieza por cada check-in, haya o no
check-out previo. La ventana la cierra el check-in de la reserva y la abre la salida de la
reserva anterior del mismo apartamento; si no hay reserva anterior, no hay salida que
esperar y la ventana se abre el lunes de la semana del check-in.
"""

from datetime import date, datetime, timedelta

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


def _same_week(date1: date, date2: date) -> bool:
    """True si ambas fechas caen en la misma semana (lunes a domingo)."""
    monday1 = date1 - timedelta(days=date1.weekday())
    monday2 = date2 - timedelta(days=date2.weekday())
    return monday1 == monday2


def cleaning_window_start(booking: Booking, previous: Booking | None) -> datetime:
    """Instante a partir del cual se puede limpiar para preparar la entrada de *booking*.

    La ventana se abre lo más tarde posible dentro de lo razonable:

    * Si hay reserva anterior y su check-out cae en la **misma semana** del
      check-in, la ventana se abre en ese check-out (se limpia entre la salida
      y la entrada).
    * Si la reserva anterior se fue **antes** de la semana del check-in, la
      ventana se abre el **lunes** de la semana del check-in.  No se remonta
      semanas atrás.
    * Si el **check-in es lunes**, la ventana puede empezar como muy pronto el
      **viernes de la semana anterior** (para que la limpiadora la vea al
      consultar la próxima semana desde el viernes).
    * Sin reserva anterior, el piso ya está libre: se abre el **lunes** de la
      semana del check-in.
    """
    if previous is not None:
        previous_available = previous.cleaning_available_at()
        # Si el check-out está en la misma semana que el check-in, usarlo.
        if _same_week(previous.check_out, booking.check_in):
            return previous_available

        # Si no está en la misma semana pero es reciente (dentro de la semana
        # natural anterior), también puede usarse.  Esto cubre el caso de
        # check-out el viernes anterior y check-in el lunes siguiente.
        check_in_monday = booking.check_in - timedelta(days=booking.check_in.weekday())
        one_week_before_monday = check_in_monday - timedelta(days=7)
        if previous.check_out >= one_week_before_monday:
            return previous_available

    # Sin reserva anterior, o check-out demasiado antiguo.
    # La ventana se abre el lunes de la semana del check-in.
    check_in_monday = booking.check_in - timedelta(days=booking.check_in.weekday())
    return datetime.combine(check_in_monday, DEFAULT_CHECKOUT_TIME)
