"""
Schemas de API para apartamentos
"""

from datetime import date

from pydantic import BaseModel, Field

from domain.apartments.entity import DEFAULT_ELECTRIC_ALLOWANCE_RATE


class ApartmentResponse(BaseModel):
    """
    Respuesta HTTP con la información de un apartamento
    """

    apartment_id: str = Field(description="Identificador único del apartamento")
    community: str | None = Field(default=None, description="Comunidad del apartamento")
    apartment_description: str | None = Field(
        default=None, description="Descripción del apartamento en la plataforma de reservas"
    )
    address: str | None = Field(default=None, description="Dirección del apartamento")
    rooms: int = Field(description="Número de habitaciones")
    bathrooms: int = Field(description="Número de baños")
    parking: str = Field(description="Identificador de parking")
    total_occupants: int = Field(description="Número máximo de ocupantes")
    owner_name: str | None = Field(default=None, description="Nombre del propietario")
    email: str | None = Field(default=None, description="Email del propietario")
    phone: str | None = Field(default=None, description="Teléfono del propietario")
    color: str | None = Field(
        default=None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Color personalizado en el calendario (hexadecimal #RRGGBB)",
    )
    electric_allowance_enabled: bool = Field(
        default=False,
        description="Si el apartamento aplica cupo eléctrico a sus reservas",
    )
    electric_allowance_rate: float = Field(
        default=DEFAULT_ELECTRIC_ALLOWANCE_RATE,
        ge=0,
        description="Importe por noche del cupo eléctrico",
    )


class CreateApartmentRequest(BaseModel):
    """
    Solicitud de creación de un apartamento
    """

    apartment_id: str = Field(
        ..., max_length=255, description="Identificador único del apartamento"
    )
    community: str | None = Field(
        default=None, max_length=25, description="Comunidad del apartamento"
    )
    apartment_description: str | None = Field(
        default=None,
        max_length=255,
        description="Descripción del apartamento en la plataforma de reservas",
    )
    address: str | None = Field(
        default=None, max_length=255, description="Dirección del apartamento"
    )
    rooms: int = Field(..., ge=0, description="Número de habitaciones")
    bathrooms: int = Field(..., ge=0, description="Número de baños")
    parking: str = Field(default="N/A", max_length=10, description="Identificador de parking")
    total_occupants: int = Field(default=0, ge=0, description="Número máximo de ocupantes")
    owner_name: str | None = Field(
        default=None, max_length=50, description="Nombre del propietario"
    )
    email: str | None = Field(default=None, max_length=35, description="Email del propietario")
    phone: str | None = Field(default=None, max_length=15, description="Teléfono del propietario")
    color: str | None = Field(
        default=None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Color personalizado en el calendario (hexadecimal #RRGGBB)",
    )
    electric_allowance_enabled: bool = Field(
        default=False,
        description="Si el apartamento aplica cupo eléctrico a sus reservas",
    )
    electric_allowance_rate: float = Field(
        default=DEFAULT_ELECTRIC_ALLOWANCE_RATE,
        ge=0,
        description="Importe por noche del cupo eléctrico",
    )


class UpdateApartmentRequest(BaseModel):
    """
    Solicitud de actualización de un apartamento
    """

    community: str | None = Field(
        default=None, max_length=25, description="Comunidad del apartamento"
    )
    apartment_description: str | None = Field(
        default=None,
        max_length=255,
        description="Descripción del apartamento en la plataforma de reservas",
    )
    address: str | None = Field(
        default=None, max_length=255, description="Dirección del apartamento"
    )
    rooms: int = Field(..., ge=0, description="Número de habitaciones")
    bathrooms: int = Field(..., ge=0, description="Número de baños")
    parking: str = Field(default="N/A", max_length=10, description="Identificador de parking")
    total_occupants: int = Field(default=0, ge=0, description="Número máximo de ocupantes")
    owner_name: str | None = Field(
        default=None, max_length=50, description="Nombre del propietario"
    )
    email: str | None = Field(default=None, max_length=35, description="Email del propietario")
    phone: str | None = Field(default=None, max_length=15, description="Teléfono del propietario")
    color: str | None = Field(
        default=None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Color personalizado en el calendario (hexadecimal #RRGGBB)",
    )
    electric_allowance_enabled: bool = Field(
        default=False,
        description="Si el apartamento aplica cupo eléctrico a sus reservas",
    )
    electric_allowance_rate: float = Field(
        default=DEFAULT_ELECTRIC_ALLOWANCE_RATE,
        ge=0,
        description="Importe por noche del cupo eléctrico",
    )


class ApartmentStatsRange(BaseModel):
    """Estadísticas de reservas para un rango de fechas dado."""

    start_date: date | None = None
    end_date: date | None = None
    total_bookings: int
    active_bookings: int
    cancelled_bookings: int
    cancellation_rate: float | None = None
    total_nights: int
    avg_nights_per_booking: float | None = None
    total_persons: int
    avg_persons_per_booking: float | None = None
    total_revenue: float | None = None
    avg_revenue_per_booking: float | None = None
    avg_revenue_per_night: float | None = None
    total_charges: float | None = None
    total_electric_allowance: float | None = None
    occupancy_pct: float | None = None
    status_breakdown: dict[str, int]


class ApartmentStatsYear(BaseModel):
    """Estadísticas de reservas agrupadas por año."""

    year: int
    total_bookings: int
    active_bookings: int
    cancelled_bookings: int
    cancellation_rate: float | None = None
    total_nights: int
    avg_nights_per_booking: float | None = None
    total_days_in_year: int
    occupancy_pct: float
    total_revenue: float | None = None
    avg_revenue_per_booking: float | None = None
    total_charges: float | None = None
    total_electric_allowance: float | None = None


class ApartmentStatsResponse(BaseModel):
    """Estadísticas completas de un apartamento."""

    apartment_id: str
    apartment: ApartmentResponse
    filtered_range: ApartmentStatsRange
    by_year: list[ApartmentStatsYear]
