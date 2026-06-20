"""
DTOs (Data Transfer Objects) para la API de reservas.
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class BookingResponse(BaseModel):
    """DTO de salida. Modelo de respuesta para la API."""

    model_config = ConfigDict(from_attributes=True)

    record_id: int
    apartment_id: str
    guest_name: str
    check_in: date
    check_out: date
    nights: int
    status: str
    persons: int
    adults: int
    children: int
    price: float | None = None
    charges: float | None = None
    email: str | None = None
    phone: str | None = None
    booking_number: str | None = None
    notes: str | None = None
    electric_allowance: float | None = None


class BookingStatsResponse(BaseModel):
    """Estadísticas agregadas sobre un conjunto de reservas."""

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
    status_breakdown: dict[str, int]
    start_date: date | None = None
    end_date: date | None = None
    occupancy_pct: float | None = None
    no_booking_days_pct: float | None = None


class BookingCreateRequest(BaseModel):
    """DTO de entrada para POST /bookings/."""

    apartment_id: str = Field(..., description="Referencia única del apartamento")
    guest_name: str = Field(..., min_length=1, description="Nombre completo del huésped")
    check_in: date = Field(..., description="Fecha de check-in")
    check_out: date = Field(..., description="Fecha de check-out")
    nights: int = Field(..., ge=1, description="Número de noches")
    status: str = Field(default="Confirmed", description="Estado de la reserva")
    persons: int = Field(default=1, ge=1)
    adults: int = Field(default=1, ge=1)
    children: int = Field(default=0, ge=0)
    price: float | None = Field(default=None, ge=0)
    charges: float | None = Field(default=None, ge=0)
    email: str | None = None
    phone: str | None = None
    booking_number: str | None = None
    notes: str | None = None


class BookingUpdateRequest(BaseModel):
    """DTO de entrada para actualización de una reserva. Todos los campos son opcionales."""

    apartment_id: str | None = None
    guest_name: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    status: str | None = None
    persons: int | None = None
    adults: int | None = None
    children: int | None = None
    price: float | None = None
    charges: float | None = None
    email: str | None = None
    phone: str | None = None
    booking_number: str | None = None
    notes: str | None = None
