"""
DTOs para la API de búsquedas avanzadas.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from api.v1.bookings.schemas import BookingResponse

DateMode = Literal["movement", "check_in", "check_out", "stay"]
SortDir = Literal["asc", "desc"]


class ApartmentSearchResponse(BaseModel):
    """
    DTO de salida para la búsqueda de apartamentos.
    """

    model_config = ConfigDict(from_attributes=True)

    booking_id: str
    community: str | None = None
    booking_name: str | None = None
    address: str | None = None
    bedrooms: int
    bathrooms: int
    parking: str
    total_occupancy: int
    owner_name: str | None = None
    owner_email: str | None = None
    owner_phone: str | None = None


class BookingSearchItemResponse(BookingResponse):
    """
    Respuesta devuelva por la búsqueda enriquecida con los datos del apartamento
    """

    apartment: ApartmentSearchResponse | None = None


class BookingSearchResponse(BaseModel):
    """
    Respuesta paginada del endpoint de búsqueda de reservas
    """

    items: list[BookingSearchItemResponse]
    total: int
    limit: int
    offset: int


class BookingSearchOptionsResponse(BaseModel):
    """
    Opciones disponibles para los filtros de búsqueda
    """

    booking_ids: list[str]
    statuses: list[str]


class BookingSearchFilters(BaseModel):
    """
    Filtros usados para buscar, ordenar y paginar las reservas
    """

    q: str | None = None  # Búsqueda de texto libre en campos clave
    start_date: date | None = None
    end_date: date | None = None
    date_mode: DateMode = "movement"
    booking_ids: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    sort_by: str = "check_in"
    sort_dir: SortDir = "asc"
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
