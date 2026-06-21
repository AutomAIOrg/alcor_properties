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
    Devuelve facturas virtuales 'Pendiente': exactamente las limpiezas que en la pestaña
    "Organización de limpiezas" mostrarían el botón "Generar factura".

    Para garantizar la paridad entre ambas vistas, se reutiliza el mismo cálculo de
    oportunidades de limpieza y se filtran las que aún no tienen factura activa
    (``has_bill == False``) y ya son facturables (``can_bill == True``, es decir, el
    check-out ya ha ocurrido). Una oportunidad con una factura cancelada vuelve a contar
    como pendiente y se marca con ``previously_cancelled``.
    """

    def __init__(
        self,
        booking_repository: IBookingRepository,
        bill_repository: IBillRepository,
    ) -> None:
        self._opportunities = GetCleaningOpportunitiesUseCase(booking_repository, bill_repository)

    def execute(
        self,
        apartment_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        reference_datetime: datetime | None = None,
    ) -> list[Bill]:
        opportunities = self._opportunities.execute_at(reference_datetime)

        pending: list[Bill] = []
        for opportunity in opportunities:
            # Solo las que en Org. Limpiezas mostrarían el botón "Generar factura".
            if opportunity.has_bill or not opportunity.can_bill:
                continue
            checkout = opportunity.available_from
            if apartment_id is not None and opportunity.apartment_id != apartment_id:
                continue
            if date_from is not None and checkout < date_from:
                continue
            if date_to is not None and checkout > date_to:
                continue
            pending.append(
                Bill(
                    record_id=opportunity.source_booking_record_id,
                    apartment_id=opportunity.apartment_id,
                    cleaning_date=checkout,
                    state="Pendiente",
                    previously_cancelled=opportunity.bill_state == BILL_STATE_CANCELLED,
                )
            )

        pending.sort(key=lambda b: b.cleaning_date or date.min, reverse=True)
        return pending
