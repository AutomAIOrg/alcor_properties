"""
Enrutador para las búsquedas.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.v1.searches.schemas import (
    ApartmentSearchResponse,
    BookingSearchFilters,
    BookingSearchItemResponse,
    BookingSearchOptionsResponse,
    BookingSearchResponse,
    DateMode,
    SortDir,
)
from infrastructure.database.session import get_db
from infrastructure.models.apartment import ApartmentORM
from infrastructure.models.booking import BookingORM
from infrastructure.repositories.sqlalchemy_search_repository import SQLAlchemySearchRepository

router = APIRouter(prefix="/searches", tags=["searches"])


@router.get("/bookings", response_model=BookingSearchResponse)
def search_bookings(
    q: str | None = Query(default=None),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    date_mode: DateMode = Query(default="movement"),
    booking_ids: list[str] | None = Query(default=None),
    statuses: list[str] | None = Query(default=None),
    sort_by: str = Query(default="check_in"),
    sort_dir: SortDir = Query(default="asc"),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> BookingSearchResponse:
    """
    Busca reservas enriquecidas con datos del apartamento, aplicando filtros, ordenamiento y paginación.
    """

    filters = BookingSearchFilters(
        q=q,
        start_date=start_date,
        end_date=end_date,
        date_mode=date_mode,
        booking_ids=booking_ids or [],
        statuses=statuses or [],
        sort_by=sort_by,
        sort_dir=sort_dir,
        limit=limit,
        offset=offset,
    )

    repository = SQLAlchemySearchRepository(db)
    rows, total = repository.search_bookings(filters)

    return BookingSearchResponse(
        items=[_to_booking_search_item_response(booking, apartment) for booking, apartment in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/bookings/options", response_model=BookingSearchOptionsResponse)
def get_booking_search_options(
    db: Session = Depends(get_db),
) -> BookingSearchOptionsResponse:
    """
    Devuelve las opciones disponibles para los filtros de búsqueda de reservas.
    """

    repository = SQLAlchemySearchRepository(db)
    booking_ids, statuses = repository.get_options()

    return BookingSearchOptionsResponse(
        booking_ids=booking_ids,
        statuses=statuses,
    )


# ------------------------------------------------------------------ #
# Helpers privados de conversión                                     #
# ------------------------------------------------------------------ #


def _to_booking_search_item_response(
    booking: BookingORM,
    apartment: ApartmentORM | None,
) -> BookingSearchItemResponse:
    """
    Convierte una tupla BookingORM + ApartmentORM en el DTO de respuesta.
    """

    return BookingSearchItemResponse(
        record_id=booking.record_id,
        booking_id=booking.booking_id,
        guest_name=booking.guest_name or "Unknown",
        check_in=booking.check_in,
        check_out=booking.check_out,
        nights=_resolve_nights(booking),
        status=booking.status or "Confirmed",
        persons=booking.persons or 1,
        adults=booking.adults or 1,
        children=booking.children or 0,
        price=_decimal_to_float(booking.price),
        charges=_decimal_to_float(booking.charges),
        email=booking.email,
        phone=booking.phone,
        booking_number=booking.booking_number,
        notes=booking.notes,
        electric_allowance=None,
        apartment=ApartmentSearchResponse.model_validate(apartment)
        if apartment is not None
        else None,
    )


def _resolve_nights(booking: BookingORM) -> int:
    """
    Calcula la cantidad de noches de una reserva a partir de las fechas de check-in y check-out.
    """

    if booking.nights is not None:
        return booking.nights

    return (booking.check_out - booking.check_in).days


def _decimal_to_float(value: Decimal | None) -> float | None:
    """
    Convierte valores Decimal de SQLAlchemy a float para el DTO de respuesta.
    """

    if value is None:
        return None

    return float(value)
