"""
Interfaz abstracta de repositorio para el dominio de Reservas.
"""

from abc import ABC, abstractmethod
from datetime import date

from domain.bookings.entity import Booking


class IBookingRepository(ABC):
    """Puerto para las operaciones de persistencia de reservas."""

    @abstractmethod
    def get_by_id(self, record_id: int) -> Booking:
        """
        Devuelve la reserva identificada por *record_id*.

        Excepciones:
            BookingNotFound: si no existe una reserva con ese ID.
        """
        pass

    @abstractmethod
    def search_bookings(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int | None = None,
        apartment_id: str | None = None,
        status: str | None = None,
        guest_name: str | None = None,
        booking_number: str | None = None,
    ) -> list[Booking]:
        """
        Devuelve las reservas, opcionalmente filtradas por rango de fechas y limitadas en cantidad.

        Cuando se proporcionan *start_date* / *end_date*, solo se retornan reservas cuya
        estancia se superpone con ese rango semiabierto [start_date, end_date). El resto de
        parámetros aplican filtros adicionales.
        """
        pass

    @abstractmethod
    def create(self, booking: Booking) -> Booking:
        """
        Persiste una nueva reserva y la devuelve con el *record_id* asignado.

        La *booking* recibida debe tener ``record_id=None``.
        """
        pass

    @abstractmethod
    def update(self, booking: Booking) -> Booking:
        """
        Persiste los cambios en una reserva existente y devuelve la entidad actualizada.

        Excepciones:
            BookingNotFound: si no existe una reserva con *booking.record_id*.
        """
        pass

    @abstractmethod
    def delete(self, record_id: int) -> None:
        """
        Elimina la reserva identificada por *record_id*.

        Excepciones:
            BookingNotFound: si no existe una reserva con ese ID.
        """
        pass

    @abstractmethod
    def get_all_by_apartment_id(self, apartment_id: str) -> list[Booking]:
        """
        Devuelve todas las reservas de un apartamento.
        """
        pass

    @abstractmethod
    def find_overlapping_active(
        self,
        apartment_id: str,
        check_in: date,
        check_out: date,
        exclude_record_id: int | None = None,
    ) -> bool:
        """
        Busca si hay alguna reserva activa que bloquea el apartamento en el rango de fechas proporcionado.
        """
        pass
