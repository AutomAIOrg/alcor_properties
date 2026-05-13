"""
Entidad de dominio Booking.
"""

from datetime import date, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Booking(BaseModel):
    """
    Entidad de dominio principal que representa una reserva de propiedad.

    Invariantes de negocio aplicadas aquí:
    - check_out debe ser estrictamente posterior a check_in.
    - nights siempre se deriva automáticamente de la diferencia de fechas para mantener la consistencia.
    """

    model_config = ConfigDict(frozen=False)

    record_id: Optional[int] = Field(
        default=None,
        description="Clave primaria de base de datos. None para entidades aún no persistidas.",
    )
    booking_id: str = Field(..., description="Identificador único de la reserva (ej. referencia Airbnb)")
    guest_name: str = Field(..., min_length=1, description="Nombre completo del huésped")
    check_in: date = Field(..., description="Fecha de entrada (inclusiva)")
    check_out: date = Field(..., description="Fecha de salida (exclusiva)")
    nights: int = Field(..., ge=1, description="Número de noches — derivado de las fechas")
    status: str = Field(default="Confirmed", description="Estado de la reserva")

    # Ocupación
    persons: int = Field(default=1, ge=1, description="Número total de personas")
    adults: int = Field(default=1, ge=1, description="Número de adultos")
    children: int = Field(default=0, ge=0, description="Número de niños")

    # Financiero
    price: Optional[float] = Field(default=None, ge=0, description="Precio total")
    charges: Optional[float] = Field(default=None, ge=0, description="Comisión y cargos")

    # Contacto
    email: Optional[str] = Field(default=None, description="Correo electrónico del huésped")
    phone: Optional[str] = Field(default=None, description="Teléfono del huésped")

    # Metadatos
    booking_number: Optional[str] = Field(default=None, description="Referencia de reserva de la plataforma")
    notes: Optional[str] = Field(default=None, description="Notas en texto libre")

    # Campo calculado — establecido por la capa de aplicación, no persistido en la BD
    electric_allowance: Optional[float] = Field(
        default=None,
        description="Bonificación eléctrica (noches × 4 €) cuando aplica",
    )

    # ------------------------------------------------------------------ #
    # Validadores                                                        #
    # ------------------------------------------------------------------ #

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v: date, info) -> date:
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("check_out debe ser estrictamente posterior a check_in")
        return v

    @field_validator("nights")
    @classmethod
    def nights_derived_from_dates(cls, v: int, info) -> int:
        """Corrige automáticamente el número de noches para que siempre coincida con la diferencia real de fechas."""
        if "check_in" in info.data and "check_out" in info.data:
            return (info.data["check_out"] - info.data["check_in"]).days
        return v

    # ------------------------------------------------------------------ #
    # Comportamiento de dominio                                          #
    # ------------------------------------------------------------------ #

    def is_active(self, reference_date: Optional[date] = None) -> bool:
        """Devuelve True si la reserva cubre *reference_date* (por defecto hoy)."""
        today = reference_date or date.today()
        return self.check_in <= today <= self.check_out

    def is_cancelled(self) -> bool:
        return self.status.lower() == "cancelled"

    def has_upcoming_checkin(self, days: int = 7, reference_date: Optional[date] = None) -> bool:
        """Devuelve True si el check-in es en los próximos *days* días."""
        today = reference_date or date.today()
        return today <= self.check_in <= today + timedelta(days=days)

    def has_upcoming_checkout(self, days: int = 7, reference_date: Optional[date] = None) -> bool:
        """Devuelve True si el check-out es en los próximos *days* días."""
        today = reference_date or date.today()
        return today <= self.check_out <= today + timedelta(days=days)
