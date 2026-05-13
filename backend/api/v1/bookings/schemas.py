"""
DTOs (Data Transfer Objects) para la API de reservas.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class BookingResponse(BaseModel):
    """DTO de salida. Modelo de respuesta para la API."""

    model_config = ConfigDict(from_attributes=True)

    record_id: int
    booking_id: str
    guest_name: str
    check_in: date
    check_out: date
    nights: int
    status: str
    persons: int
    adults: int
    children: int
    price: Optional[float] = None
    charges: Optional[float] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_number: Optional[str] = None
    notes: Optional[str] = None
    electric_allowance: Optional[float] = None


class BookingCreateRequest(BaseModel):
    """DTO de entrada para POST /bookings/."""

    booking_id: str = Field(..., description="Referencia única de la reserva")
    guest_name: str = Field(..., min_length=1, description="Nombre completo del huésped")
    check_in: date = Field(..., description="Fecha de check-in")
    check_out: date = Field(..., description="Fecha de check-out")
    nights: int = Field(..., ge=1, description="Número de noches")
    status: str = Field(default="Confirmed", description="Estado de la reserva")
    persons: int = Field(default=1, ge=1)
    adults: int = Field(default=1, ge=1)
    children: int = Field(default=0, ge=0)
    price: Optional[float] = Field(default=None, ge=0)
    charges: Optional[float] = Field(default=None, ge=0)
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_number: Optional[str] = None
    notes: Optional[str] = None


class BookingUpdateRequest(BaseModel):
    """DTO de entrada para actualización de una reserva. Todos los campos son opcionales."""

    booking_id: Optional[str] = None
    guest_name: Optional[str] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    status: Optional[str] = None
    persons: Optional[int] = None
    adults: Optional[int] = None
    children: Optional[int] = None
    price: Optional[float] = None
    charges: Optional[float] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    booking_number: Optional[str] = None
    notes: Optional[str] = None
