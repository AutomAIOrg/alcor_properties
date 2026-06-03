"""
Caso de uso para buscar apartamentos disponibles según filtros.
"""

from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from domain.apartments.repository import IApartmentRepository


class SearchApartmentsQuery:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(
        self,
        filters: ApartmentSearchFilters,
    ) -> list[Apartment]:
        return self.apartment_repository.search_apartments(filters)


class GetApartmentByBookingIdQuery:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(self, booking_id: str) -> Apartment | None:
        booking_id = booking_id.strip()

        if not booking_id:
            raise ValueError("El booking_id no puede estar vacío")

        return self.apartment_repository.get_by_booking_id(booking_id)
