"""
Caso de uso para buscar apartamentos disponibles según filtros.
"""

import logging

from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from domain.apartments.repository import IApartmentRepository
from domain.bookings.repository import IBookingRepository
from domain.exceptions import (
    ApartmentAlreadyExistsError,
    ApartmentHasBookingsError,
    ApartmentNotFoundError,
)

logger = logging.getLogger(__name__)


class CreateApartmentUseCase:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(self, new_apartment: Apartment) -> None:
        apartment = self.apartment_repository.get_by_apartment_id(new_apartment.apartment_id)
        if apartment is not None:
            raise ApartmentAlreadyExistsError(new_apartment.apartment_id)

        self.apartment_repository.create_apartment(new_apartment)


class DeleteApartmentUseCase:
    def __init__(
        self,
        apartment_repository: IApartmentRepository,
        booking_repository: IBookingRepository,
    ) -> None:
        self.apartment_repository = apartment_repository
        self.booking_repository = booking_repository

    def execute(self, apartment_id: str) -> None:
        apartment = self.apartment_repository.get_by_apartment_id(apartment_id)
        if apartment is None:
            raise ApartmentNotFoundError(apartment_id)

        bookings = self.booking_repository.get_all_by_apartment_id(apartment_id)
        for booking in bookings:
            if booking.blocks_apartment_deletion():
                raise ApartmentHasBookingsError(apartment_id)

        self.apartment_repository.delete_apartment(apartment)


class UpdateApartmentUseCase:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(self, updated_apartment: Apartment) -> None:
        apartment = self.apartment_repository.get_by_apartment_id(updated_apartment.apartment_id)
        if apartment is None:
            raise ApartmentNotFoundError(updated_apartment.apartment_id)

        self.apartment_repository.update_apartment(updated_apartment)


class SearchApartmentsUseCase:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(
        self,
        filters: ApartmentSearchFilters,
    ) -> list[Apartment]:
        return self.apartment_repository.search_apartments(filters)


class GetApartmentByIdUseCase:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(self, apartment_id: str) -> Apartment | None:
        apartment_id = apartment_id.strip()

        if not apartment_id:
            raise ValueError("El apartment_id no puede estar vacío")

        return self.apartment_repository.get_by_apartment_id(apartment_id)


class GetAllApartmentsUseCase:
    def __init__(self, apartment_repository: IApartmentRepository) -> None:
        self.apartment_repository = apartment_repository

    def execute(self) -> list[Apartment]:
        apartments = self.apartment_repository.get_all()
        return apartments
