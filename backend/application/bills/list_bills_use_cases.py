"""
Casos de uso de lectura (consultas) para el dominio de Facturas.
"""

from datetime import date, datetime

from application.bookings.queries import GetCleaningOpportunitiesUseCase
from domain.apartments.repository import IApartmentRepository
from domain.bills.entity import BILL_STATE_CANCELLED, BILL_STATE_PENDING, Bill
from domain.bills.repository import IBillRepository
from domain.bookings.repository import IBookingRepository


def enrich_with_apartment_data(
    bills: list[Bill],
    apartment_repository: IApartmentRepository | None,
) -> list[Bill]:
    """Copia dirección y descripción del apartamento en cada factura (para el recibo)."""
    if apartment_repository is None or not bills:
        return bills

    apartments_by_id = {
        apartment.apartment_id: apartment for apartment in apartment_repository.get_all()
    }

    enriched: list[Bill] = []
    for bill in bills:
        apartment = apartments_by_id.get(bill.apartment_id)
        if apartment is None:
            enriched.append(bill)
            continue
        enriched.append(
            bill.model_copy(
                update={
                    "address": apartment.address,
                    "apartment_description": apartment.apartment_description,
                }
            )
        )
    return enriched


class ListBillsUseCase:
    """Devuelve facturas reales con filtrado opcional."""

    def __init__(
        self,
        bill_repository: IBillRepository,
        apartment_repository: IApartmentRepository | None = None,
    ) -> None:
        self._bill_repository = bill_repository
        self._apartment_repository = apartment_repository

    def execute(
        self,
        apartment_id: str | None = None,
        state: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        cost_min: float | None = None,
        cost_max: float | None = None,
    ) -> list[Bill]:
        bills = self._bill_repository.list(
            apartment_id=apartment_id,
            state=state,
            date_from=date_from,
            date_to=date_to,
            cost_min=cost_min,
            cost_max=cost_max,
        )
        return enrich_with_apartment_data(bills, self._apartment_repository)


class ListPendingBillsUseCase:
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
        apartment_repository: IApartmentRepository | None = None,
    ) -> None:
        self._get_cleaning_opportunities_use_case = GetCleaningOpportunitiesUseCase(
            booking_repository,
            bill_repository,
            apartment_repository,
        )

    def execute(
        self,
        apartment_id: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        reference_datetime: datetime | None = None,
    ) -> list[Bill]:
        opportunities = self._get_cleaning_opportunities_use_case.execute_at(reference_datetime)

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
                    state=BILL_STATE_PENDING,
                    previously_cancelled=opportunity.bill_state == BILL_STATE_CANCELLED,
                    address=opportunity.address,
                    apartment_description=opportunity.apartment_description,
                )
            )

        pending.sort(key=lambda b: b.cleaning_date or date.min, reverse=True)
        return pending
