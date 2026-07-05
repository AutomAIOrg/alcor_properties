"""
Caso de uso para buscar apartamentos disponibles según filtros.
"""

import calendar
import logging
from datetime import date

from application.bookings.helpers import (
    apply_all,
    booking_overlap_nights,
    compute_stats,
    count_days_without_bookings,
)
from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from domain.apartments.repository import IApartmentRepository
from domain.bookings.entity import Booking
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


def _booking_years(booking: Booking) -> range:
    return range(booking.check_in.year, booking.check_out.year + 1)


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


class GetApartmentStatsUseCase:
    """
    Calcula estadísticas de un apartamento: métricas del rango filtrado y desglose anual.

    - filtered_range: stats de las reservas que se superponen con el rango proporcionado.
        Incluye occupancy_pct = noches_activas / días_del_rango × 100 (solo si hay fechas).
    - by_year: cubre TODOS los años con reservas del apartamento (ignora el filtro de fechas).
        occupancy_pct = noches_activas / días_del_año × 100.
    """

    def __init__(
        self,
        apartment_repository: IApartmentRepository,
        booking_repository: IBookingRepository,
        electric_apartment_ids: set[str],
    ) -> None:
        self._apt_repo = apartment_repository
        self._bkg_repo = booking_repository
        self._electric_ids = electric_apartment_ids

    def execute(
        self,
        apartment_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        # Verificar que el apartamento existe
        apartment = self._apt_repo.get_by_apartment_id(apartment_id)
        if apartment is None:
            raise ApartmentNotFoundError(apartment_id)

        # Reservas del rango filtrado (o todas si no hay rango)
        if start_date and end_date:
            range_bookings = self._bkg_repo.search_bookings(
                start_date=start_date,
                end_date=end_date,
                apartment_id=apartment_id,
            )
        else:
            range_bookings = self._bkg_repo.search_bookings(apartment_id=apartment_id)

        range_bookings = apply_all(range_bookings, self._electric_ids)

        # Calcular occupancy_pct del rango
        range_occupancy_pct = None
        if start_date and end_date:
            range_days = (end_date - start_date).days
            if range_days > 0:
                days_without = count_days_without_bookings(range_bookings, start_date, end_date)
                range_occupancy_pct = round((range_days - days_without) / range_days * 100, 2)

        filtered_range = compute_stats(
            range_bookings,
            start_date=start_date,
            end_date=end_date,
            occupancy_pct=range_occupancy_pct,
        )

        # Todas las reservas del apartamento (para el desglose anual)
        all_bookings = apply_all(
            self._bkg_repo.search_bookings(apartment_id=apartment_id),
            self._electric_ids,
        )

        # Agrupar por años tocados por la estancia. Una reserva que cruza de año
        # contribuye a cada año solo con las noches e importes proporcionales.
        by_year_map: dict[int, list[Booking]] = {}
        for booking in all_bookings:
            for yr in _booking_years(booking):
                year_start = date(yr, 1, 1)
                year_end = date(yr + 1, 1, 1)
                if booking_overlap_nights(booking, year_start, year_end) > 0:
                    by_year_map.setdefault(yr, []).append(booking)

        by_year = []
        for yr in sorted(by_year_map.keys()):
            year_bookings = by_year_map[yr]
            total_days_in_year = 366 if calendar.isleap(yr) else 365
            year_start = date(yr, 1, 1)
            year_end = date(yr + 1, 1, 1)

            active = [b for b in year_bookings if b.status.lower() != "cancelled"]
            active_year_nights = [
                (b, booking_overlap_nights(b, year_start, year_end)) for b in active
            ]
            total_nights = sum(nights for _, nights in active_year_nights)
            days_without = count_days_without_bookings(year_bookings, year_start, year_end)
            occupancy_pct = round((total_days_in_year - days_without) / total_days_in_year * 100, 2)

            cancelled_count = len(year_bookings) - len(active)
            total = len(year_bookings)
            cancellation_rate = round(cancelled_count / total * 100, 2) if total > 0 else None

            avg_nights = round(total_nights / len(active), 2) if active else None

            prices = [
                float(b.price) * year_nights / b.nights
                for b, year_nights in active_year_nights
                if b.price is not None
            ]
            total_revenue = round(sum(prices), 2) if prices else None
            avg_rev_booking = (
                round(total_revenue / len(prices), 2)
                if total_revenue is not None and prices
                else None
            )

            charges = [
                float(b.charges) * year_nights / b.nights
                for b, year_nights in active_year_nights
                if b.charges is not None
            ]
            total_charges = round(sum(charges), 2) if charges else None

            electric = [
                float(b.electric_allowance) * year_nights / b.nights
                for b, year_nights in active_year_nights
                if b.electric_allowance is not None
            ]
            total_electric = round(sum(electric), 2) if electric else None

            by_year.append(
                {
                    "year": yr,
                    "total_bookings": total,
                    "active_bookings": len(active),
                    "cancelled_bookings": cancelled_count,
                    "cancellation_rate": cancellation_rate,
                    "total_nights": total_nights,
                    "avg_nights_per_booking": avg_nights,
                    "total_days_in_year": total_days_in_year,
                    "occupancy_pct": occupancy_pct,
                    "total_revenue": total_revenue,
                    "avg_revenue_per_booking": avg_rev_booking,
                    "total_charges": total_charges,
                    "total_electric_allowance": total_electric,
                }
            )

        return {
            "apartment_id": apartment_id,
            "apartment": apartment.model_dump(),
            "filtered_range": filtered_range,
            "by_year": by_year,
        }
