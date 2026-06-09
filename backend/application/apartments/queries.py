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


class GetApartmentByIdQuery:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(self, apartment_id: str) -> Apartment | None:
        apartment_id = apartment_id.strip()

        if not apartment_id:
            raise ValueError("El apartment_id no puede estar vacío")

        return self.apartment_repository.get_by_apartment_id(apartment_id)
