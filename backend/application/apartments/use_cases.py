"""
Caso de uso para buscar apartamentos disponibles según filtros.
"""

import calendar
from datetime import date

from application.bookings.queries import _apply_all, _compute_stats
from domain.apartments.entity import Apartment
from domain.apartments.filters import ApartmentSearchFilters
from domain.apartments.repository import IApartmentRepository
from domain.bookings.entity import Booking
from domain.bookings.repository import IBookingRepository
from domain.exceptions import ApartmentNotFound


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
            raise ApartmentNotFound(apartment_id)

        # Reservas del rango filtrado (o todas si no hay rango)
        if start_date and end_date:
            range_bookings = self._bkg_repo.list(
                start_date=start_date,
                end_date=end_date,
                apartment_id=apartment_id,
            )
        else:
            range_bookings = self._bkg_repo.list(apartment_id=apartment_id)

        range_bookings = _apply_all(range_bookings, self._electric_ids)

        # Calcular occupancy_pct del rango
        range_occupancy_pct = None
        if start_date and end_date:
            range_days = (end_date - start_date).days
            if range_days > 0:
                active = [b for b in range_bookings if b.status.lower() != "cancelled"]
                total_nights = sum(b.nights for b in active)
                range_occupancy_pct = round(total_nights / range_days * 100, 2)

        filtered_range = _compute_stats(
            range_bookings,
            start_date=start_date,
            end_date=end_date,
            occupancy_pct=range_occupancy_pct,
        )

        # Todas las reservas del apartamento (para el desglose anual)
        all_bookings = _apply_all(
            self._bkg_repo.list(apartment_id=apartment_id),
            self._electric_ids,
        )

        # Agrupar por año de check_in
        by_year_map: dict[int, list[Booking]] = {}
        for b in all_bookings:
            yr = b.check_in.year
            by_year_map.setdefault(yr, []).append(b)

        by_year = []
        for yr in sorted(by_year_map.keys()):
            year_bookings = by_year_map[yr]
            total_days_in_year = 366 if calendar.isleap(yr) else 365

            active = [b for b in year_bookings if b.status.lower() != "cancelled"]
            total_nights = sum(b.nights for b in active)
            occupancy_pct = round(total_nights / total_days_in_year * 100, 2)

            cancelled_count = len(year_bookings) - len(active)
            total = len(year_bookings)
            cancellation_rate = round(cancelled_count / total * 100, 2) if total > 0 else None

            avg_nights = round(total_nights / len(active), 2) if active else None

            prices = [float(b.price) for b in active if b.price is not None]
            total_revenue = round(sum(prices), 2) if prices else None
            avg_rev_booking = round(total_revenue / len(active), 2) if total_revenue is not None and active else None

            charges = [float(b.charges) for b in active if b.charges is not None]
            total_charges = round(sum(charges), 2) if charges else None

            electric = [float(b.electric_allowance) for b in active if b.electric_allowance is not None]
            total_electric = round(sum(electric), 2) if electric else None

            by_year.append({
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
            })

        return {
            "apartment_id": apartment_id,
            "apartment": apartment.model_dump(),
            "filtered_range": filtered_range,
            "by_year": by_year,
        }
