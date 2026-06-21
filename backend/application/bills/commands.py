"""
Casos de uso (comandos) para el dominio de Facturas.
"""

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from domain.bills.entity import (
    ALLOWED_BILL_TRANSITIONS,
    BILL_STATE_PAID,
    Bill,
)
from domain.bills.repository import IBillRepository
from domain.bookings.repository import IBookingRepository
from domain.exceptions import BillAlreadyExists, DomainValidationError

_SECONDS_PER_HOUR = Decimal(3600)


@dataclass
class CreateBillData:
    """Datos crudos capturados en el modal de generación de factura."""

    record_id: int
    cleaning_date: date
    start_time: time
    end_time: time
    hourly_rate: Decimal | None = None


class CreateBillUseCase:
    """
    Genera una factura a partir de una limpieza.

    A partir de la reserva (record_id) y del intervalo horario introducido en el
    modal, deriva automáticamente:
    - apartment_id: copiado de la reserva (fuente de verdad).
    - cleaning_date: la fecha de la limpieza.
    - clean_hours: duración del intervalo (admite fracciones).
    - cost: clean_hours × tarifa por hora configurada.
    - state: "Creada".
    """

    def __init__(
        self,
        bill_repository: IBillRepository,
        booking_repository: IBookingRepository,
        cleaning_hourly_rate: Decimal,
    ) -> None:
        self._bills = bill_repository
        self._bookings = booking_repository
        self._hourly_rate = cleaning_hourly_rate

    def execute(self, data: CreateBillData) -> Bill:
        # La reserva debe existir; de ella se obtiene el apartamento (lanza BookingNotFound).
        booking = self._bookings.get_by_id(data.record_id)

        # Una limpieza solo puede facturarse una vez (las canceladas no cuentan).
        if self._bills.exists_for_booking(data.record_id):
            raise BillAlreadyExists(data.record_id)

        # Si hubo una factura cancelada para esta reserva, la eliminamos para liberar el UNIQUE.
        self._bills.delete_cancelled_for_booking(data.record_id)

        rate = data.hourly_rate if data.hourly_rate is not None else self._hourly_rate
        clean_hours = self._compute_hours(data.cleaning_date, data.start_time, data.end_time)
        cost = (clean_hours * rate).quantize(Decimal("0.01"))

        bill = Bill(
            record_id=booking.record_id,
            apartment_id=booking.apartment_id,
            cleaning_date=data.cleaning_date,
            clean_hours=clean_hours,
            cost=cost,
            hourly_rate=rate.quantize(Decimal("0.01")),
            state="Creada",
        )
        return self._bills.create(bill)

    @staticmethod
    def _compute_hours(cleaning_date: date, start_time: time, end_time: time) -> Decimal:
        start = datetime.combine(cleaning_date, start_time)
        end = datetime.combine(cleaning_date, end_time)
        if end <= start:
            raise DomainValidationError("La hora de fin debe ser posterior a la hora de inicio.")
        seconds = Decimal((end - start).total_seconds())
        return (seconds / _SECONDS_PER_HOUR).quantize(Decimal("0.01"))


class UpdateBillStateUseCase:
    """
    Cambia el estado de una factura existente aplicando las transiciones permitidas.

    La fecha de pago se registra automáticamente al pasar a "Pagada" (por defecto hoy,
    o la indicada explícitamente) y se limpia en cualquier otro estado.
    """

    def __init__(self, bill_repository: IBillRepository) -> None:
        self._bills = bill_repository

    def execute(self, bill_id: int, new_state: str, paid_at: date | None = None) -> Bill:
        bill = self._bills.get_by_id(bill_id)  # lanza BillNotFound si no existe

        allowed = ALLOWED_BILL_TRANSITIONS.get(bill.state, set())
        if new_state not in allowed:
            raise DomainValidationError(
                f"No se puede cambiar el estado de '{bill.state}' a '{new_state}'."
            )

        resolved_paid_at = (paid_at or date.today()) if new_state == BILL_STATE_PAID else None

        updated = bill.model_copy(update={"state": new_state, "paid_at": resolved_paid_at})
        return self._bills.update(updated)
