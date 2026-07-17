from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

from domain.bills.entity import BILL_STATE_CREATED, Bill
from domain.bills.repository import IBillRepository
from domain.bookings.cleaning import cleaning_window_start, find_previous_booking
from domain.bookings.repository import IBookingRepository
from domain.cleaning_types.repository import ICleaningTypeRepository
from domain.exceptions import (
    BillAlreadyExistsError,
    CleaningTypeNotFoundError,
    DomainValidationError,
)

_SECONDS_PER_HOUR = Decimal(3600)


@dataclass
class CreateBillData:
    """Datos crudos capturados en el modal de generación de factura."""

    record_id: int
    cleaning_date: date
    start_time: time
    end_time: time
    cleaning_type_id: int


class CreateBillUseCase:
    """
    Genera una factura a partir de una limpieza.

    A partir de la reserva (record_id), del intervalo horario y del tipo de limpieza
    seleccionado en el modal, deriva automáticamente:
    - apartment_id: copiado de la reserva (fuente de verdad).
    - cleaning_date: la fecha de la limpieza.
    - clean_hours: duración del intervalo (admite fracciones).
    - hourly_rate: tarifa por hora del tipo de limpieza elegido (se congela en la factura).
    - cleaning_type_name: nombre del tipo, congelado como snapshot histórico.
    - cost: clean_hours × hourly_rate.
    - state: "Creada".
    """

    def __init__(
        self,
        bill_repository: IBillRepository,
        booking_repository: IBookingRepository,
        cleaning_type_repository: ICleaningTypeRepository,
    ) -> None:
        self._bill_repository = bill_repository
        self._booking_repository = booking_repository
        self._cleaning_type_repository = cleaning_type_repository

    def execute(self, data: CreateBillData) -> Bill:
        # La reserva debe existir; de ella se obtiene el apartamento (lanza BookingNotFound).
        booking = self._booking_repository.get_by_id(data.record_id)

        if booking.is_cancelled():
            raise DomainValidationError("No se puede facturar una reserva cancelada.")

        # La limpieza prepara la entrada de esta reserva: solo puede facturarse una vez el piso
        # está libre, es decir, tras la salida de la reserva anterior (o desde el lunes de la
        # semana si no hay ninguna anterior).
        #
        # Aquí se buscan TODAS las reservas del apartamento, mientras que la lista de limpiezas
        # solo mira las de los últimos 28 días. Ese conjunto mayor es siempre un superconjunto,
        # así que la ventana que sale aquí empieza igual o antes: este check nunca puede
        # rechazar una limpieza que la pantalla sí ofrece.
        previous = find_previous_booking(
            booking, self._booking_repository.get_all_by_apartment_id(booking.apartment_id)
        )
        if datetime.now() < cleaning_window_start(booking, previous):
            raise DomainValidationError(
                "La limpieza aún no puede facturarse: su ventana no ha empezado todavía."
            )

        # El tipo de limpieza debe existir y estar activo para facturar con él.
        cleaning_type = self._cleaning_type_repository.get_by_id(data.cleaning_type_id)
        if cleaning_type is None:
            raise CleaningTypeNotFoundError(data.cleaning_type_id)
        if not cleaning_type.active:
            raise DomainValidationError(
                f"El tipo de limpieza '{cleaning_type.name}' está inactivo y no puede facturarse."
            )

        # Una limpieza solo puede facturarse una vez (las canceladas no cuentan).
        if self._bill_repository.exists_for_booking(data.record_id):
            raise BillAlreadyExistsError(data.record_id)

        # Si hubo una factura cancelada para esta reserva, la eliminamos para liberar el UNIQUE.
        self._bill_repository.delete_cancelled_for_booking(data.record_id)

        rate = cleaning_type.hourly_rate
        clean_hours = self._compute_hours(data.cleaning_date, data.start_time, data.end_time)
        cost = (clean_hours * rate).quantize(Decimal("0.01"))

        bill = Bill(
            record_id=booking.record_id,
            apartment_id=booking.apartment_id,
            cleaning_date=data.cleaning_date,
            clean_hours=clean_hours,
            cost=cost,
            hourly_rate=rate.quantize(Decimal("0.01")),
            cleaning_type_id=cleaning_type.cleaning_type_id,
            cleaning_type_name=cleaning_type.name,
            state=BILL_STATE_CREATED,
            created_at=date.today(),
        )
        return self._bill_repository.create(bill)

    @staticmethod
    def _compute_hours(cleaning_date: date, start_time: time, end_time: time) -> Decimal:
        start = datetime.combine(cleaning_date, start_time)
        end = datetime.combine(cleaning_date, end_time)
        if end <= start:
            raise DomainValidationError("La hora de fin debe ser posterior a la hora de inicio.")
        seconds = Decimal((end - start).total_seconds())
        return (seconds / _SECONDS_PER_HOUR).quantize(Decimal("0.01"))
