"""
Caso de uso para buscar apartamentos disponibles según filtros.
"""

from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from domain.apartments.repository import IApartmentRepository


class SearchApartments:

    def __init__(
            self,
            apartment_repository: IApartmentRepository
        ) -> None:
            self.apartment_repository = apartment_repository

    def execute(
            self,
            filters: ApartmentSearchFilters,
    ) -> list[Apartment]:
          return self.apartment_repository.search_apartments(filters)
