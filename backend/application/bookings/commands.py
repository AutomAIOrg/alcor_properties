"""
Casos de uso (comandos) para el dominio de Reservas.
"""

from dataclasses import dataclass
from datetime import date

from domain.bookings.entity import Booking
from domain.bookings.repository import IBookingRepository


@dataclass
class BookingUpdateData:
    apartment_id: str | None = None
    guest_name: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    status: str | None = None
    persons: int | None = None
    adults: int | None = None
    children: int | None = None
    price: float | None = None
    charges: float | None = None
    email: str | None = None
    phone: str | None = None
    booking_number: str | None = None
    notes: str | None = None


def _apply_electric_allowance(booking: Booking, electric_ids: set[str]) -> Booking:
    """Establece electric_allowance en una reserva según los IDs configurados."""
    if booking.apartment_id.strip() in electric_ids:
        booking.electric_allowance = booking.nights * 4.0
    else:
        booking.electric_allowance = None
    return booking


class CreateBookingUseCase:
    """Persiste una nueva reserva y la devuelve con la bonificación eléctrica aplicada."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

    def execute(self, booking: Booking) -> Booking:
        created = self._repo.create(booking)
        return _apply_electric_allowance(created, self._electric_ids)


class UpdateBookingUseCase:
    """Aplica una actualización parcial sobre una reserva existente."""

    def __init__(
        self,
        repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._repo = repository
        self._electric_ids = electric_apartment_ids

    def execute(self, record_id: int, data: BookingUpdateData) -> Booking:
        existing = self._repo.get_by_id(record_id)  # lanza BookingNotFound si no existe

        updates = {k: v for k, v in vars(data).items() if v is not None}

        # Revalida usando model_validate para que el validador de nights se aplique si cambian las fechas.
        updated = Booking.model_validate({**existing.model_dump(), **updates})

        saved = self._repo.update(updated)
        return _apply_electric_allowance(saved, self._electric_ids)


class DeleteBookingUseCase:
    """Elimina una reserva por su ID en base de datos."""

    def __init__(self, repository: IBookingRepository) -> None:
        self._repo = repository

    def execute(self, record_id: int) -> None:
        self._repo.delete(record_id)  # lanza BookingNotFound si no existe
