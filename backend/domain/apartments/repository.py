"""
Interfaz abstracta de repositorio para el dominio de Apartamentos.
"""

from abc import ABC, abstractmethod

from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters


class IApartmentRepository(ABC):
    """Puerto para las operaciones de persistencia de apartamentos."""

    @abstractmethod
    def get_by_booking_id(self, booking_id: str) -> Apartment | None:
        """
        Devuelve el apartamento asociado a booking_id.
        """
        pass

    @abstractmethod
    def search_apartments(
        self,
        filters: ApartmentSearchFilters,
    ) -> list[Apartment]:
        """
        Devuelve la lista de apartamentos disponibles.
        """
        pass
