"""
Casos de uso de lectura (consultas) para el dominio de Facturas.
"""

from datetime import date, datetime

from application.bookings.queries import GetCleaningOpportunitiesUseCase
from domain.bills.entity import BILL_STATE_CANCELLED, Bill
from domain.bills.repository import IBillRepository
from domain.bookings.repository import IBookingRepository


class ListBillsQuery:
    """Devuelve facturas reales con filtrado opcional."""

    def __init__(self, repository: IBillRepository) -> None:
        self._repo = repository

    def execute(
        self,
        apartment_id: str | None = None,
        state: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        cost_min: float | None = None,
        cost_max: float | None = None,
    ) -> list[Bill]:
        return self._repo.list(
            apartment_id=apartment_id,
            state=state,
            date_from=date_from,
            date_to=date_to,
            cost_min=cost_min,
            cost_max=cost_max,
        )


class ListPendingBillsQuery:
    """
    Devuelve facturas virtuales 'Pendiente' para reservas cuya limpieza ya puede facturarse.

    Una limpieza es facturable cuando el check-out ya ha ocurrido (considerando la hora de
    salida por defecto). La lista nunca retrocede más allá del lunes de la semana en curso:
    los check-outs anteriores a esa semana dejan de mostrarse como pendientes.
    """

    def __init__(
        self,
        booking_repository: IBookingRepository,
        bill_repository: IBillRepository,
    ) -> None:
        self._bookings = booking_repository
        self._bills = bill_repository

    def execute(
        self,
        apartment_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        reference_datetime: datetime | None = None,
    ) -> list[Bill]:
        now = reference_datetime or datetime.now()
        today = now.date()
        week_start = today - timedelta(days=today.weekday())
        lower_bound = max(week_start, date_from) if date_from else week_start

        bookings = self._bookings.list(
            start_date=week_start - timedelta(days=1),
            end_date=today + timedelta(days=1),
            apartment_id=apartment_id,
        )

        billed_ids = self._bills.list_billed_booking_ids()
        bill_states = self._bills.get_bill_states_by_booking()

        pending: list[Bill] = []
        for booking in bookings:
            if booking.record_id is None or booking.record_id in billed_ids:
                continue
            if booking.is_cancelled():
                continue
            if not booking.is_cleanable(now):
                continue
            checkout = booking.check_out
            if checkout < lower_bound:
                continue
            if date_to and checkout > date_to:
                continue
            pending.append(
                Bill(
                    record_id=booking.record_id,
                    apartment_id=booking.apartment_id,
                    cleaning_date=checkout,
                    state="Pendiente",
                    previously_cancelled=bill_states.get(booking.record_id) == BILL_STATE_CANCELLED,
                )
            )

        pending.sort(key=lambda b: b.cleaning_date or date.min, reverse=True)
        return pending
