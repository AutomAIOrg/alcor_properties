"""
Casos de uso (comandos) para el dominio de Reservas.
"""

from dataclasses import dataclass
from datetime import date, time

from application.bookings.helpers import apply_electric_allowance
from domain.bookings.entity import Booking
from domain.bookings.repository import IBookingRepository
from domain.exceptions import BookingConflict


class _UnsetType:
    pass


_UNSET = _UnsetType()


@dataclass
class BookingUpdateData:
    apartment_id: str | None | _UnsetType = _UNSET
    guest_name: str | None | _UnsetType = _UNSET
    check_in: date | None | _UnsetType = _UNSET
    check_out: date | None | _UnsetType = _UNSET
    check_in_time: time | None | _UnsetType = _UNSET
    check_out_time: time | None | _UnsetType = _UNSET
    status: str | None | _UnsetType = _UNSET
    persons: int | None | _UnsetType = _UNSET
    adults: int | None | _UnsetType = _UNSET
    children: int | None | _UnsetType = _UNSET
    price: float | None | _UnsetType = _UNSET
    charges: float | None | _UnsetType = _UNSET
    email: str | None | _UnsetType = _UNSET
    phone: str | None | _UnsetType = _UNSET
    booking_number: str | None | _UnsetType = _UNSET
    notes: str | None | _UnsetType = _UNSET
    notes_cleaning: str | None | _UnsetType = _UNSET

    def as_update_dict(self) -> dict[str, object]:
        """Devuelve solo los campos enviados; conserva None como limpieza explícita."""
        return {k: v for k, v in vars(self).items() if v is not _UNSET}


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
        # Validar que no haya otra reserva bloqueante para el mismo apartamento y rango de fechas
        overlapping = self._repo.find_overlapping_active(
            apartment_id=booking.apartment_id,
            check_in=booking.check_in,
            check_out=booking.check_out,
        )
        if overlapping:
            raise BookingConflict(
                check_in=str(booking.check_in),
                check_out=str(booking.check_out),
            )

        created = self._repo.create(booking)
        return apply_electric_allowance(created, self._electric_ids)


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

        updates = data.as_update_dict()

        # Revalida usando model_validate para que el validador de nights se aplique si cambian las fechas.
        updated = Booking.model_validate({**existing.model_dump(), **updates})

        if not updated.is_cancelled():
            overlapping = self._repo.find_overlapping_active(
                apartment_id=updated.apartment_id,
                check_in=updated.check_in,
                check_out=updated.check_out,
                exclude_record_id=updated.record_id,
            )
            if overlapping:
                raise BookingConflict(
                    check_in=str(updated.check_in),
                    check_out=str(updated.check_out),
                )

        saved = self._repo.update(updated)
        return apply_electric_allowance(saved, self._electric_ids)


class DeleteBookingUseCase:
    """Elimina una reserva por su ID en base de datos."""

    def __init__(self, repository: IBookingRepository) -> None:
        self._repo = repository

    def execute(self, record_id: int) -> None:
        self._repo.delete(record_id)  # lanza BookingNotFound si no existe
