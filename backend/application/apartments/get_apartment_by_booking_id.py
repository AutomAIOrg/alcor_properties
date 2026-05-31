"""
Caso de uso para obtener un apartamento por booking_id.
"""

from domain.apartments.entity import Apartment
from domain.apartments.repository import IApartmentRepository


class GetApartmentByBookingId:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(self, booking_id: str) -> Apartment | None:
        booking_id = booking_id.strip()

        if not booking_id:
            raise ValueError("El booking_id no puede estar vacío")

        return self.apartment_repository.get_by_booking_id(booking_id)
