"""
Entidad de dominio Booking.
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

# Estados de reserva que NO bloquean la disponibilidad de un apartamento.
# Una reserva en cualquiera de estos estados se considera inactiva y no impide
# que el apartamento sea reservado en el mismo período.
NON_BLOCKING_STATUSES: frozenset[str] = frozenset({"cancelled"})


class Booking(BaseModel):
    """
    Entidad de dominio principal que representa una reserva de propiedad.

    Invariantes de negocio aplicadas aquí:
    - check_out debe ser estrictamente posterior a check_in.
    - nights siempre se deriva automáticamente de la diferencia de fechas para mantener la consistencia.
    """

    model_config = ConfigDict(frozen=False)

    record_id: int | None = Field(
        default=None,
        description="Clave primaria de base de datos. None para entidades aún no persistidas.",
    )
    booking_id: str = Field(
        ..., description="Identificador único del Apartamento"
    )
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
    price: Decimal | None = Field(default=None, ge=0, description="Precio total")
    charges: Decimal | None = Field(default=None, ge=0, description="Comisión y cargos")

    # Contacto
    email: str | None = Field(default=None, description="Correo electrónico del huésped")
    phone: str | None = Field(default=None, description="Teléfono del huésped")

    # Metadatos
    booking_number: str | None = Field(
        default=None, description="Referencia de reserva de la plataforma"
    )
    notes: str | None = Field(default=None, description="Notas en texto libre")

    # Campo calculado — establecido por la capa de aplicación, no persistido en la BD
    electric_allowance: float | None = Field(
        default=None,
        description="Bonificación eléctrica (noches × 4 €) cuando aplica",
    )

    # ------------------------------------------------------------------ #
    # Validadores                                                        #
    # ------------------------------------------------------------------ #

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v: date, info: ValidationInfo) -> date:
        if "check_in" in info.data and v <= info.data["check_in"]:
            raise ValueError("check_out debe ser estrictamente posterior a check_in")
        return v

    @field_validator("nights")
    @classmethod
    def nights_derived_from_dates(cls, v: int, info: ValidationInfo) -> int:
        """Corrige automáticamente el número de noches para que siempre coincida con la diferencia real de fechas."""
        if "check_in" in info.data and "check_out" in info.data:
            data: dict[str, Any] = info.data
            delta: timedelta = data["check_out"] - data["check_in"]
            return delta.days
        return v

    # ------------------------------------------------------------------ #
    # Comportamiento de dominio                                          #
    # ------------------------------------------------------------------ #

    def is_active(self, reference_date: date | None = None) -> bool:
        """Devuelve True si la reserva cubre *reference_date* (por defecto hoy)."""
        today = reference_date or date.today()
        return self.check_in <= today <= self.check_out

    def is_cancelled(self) -> bool:
        return self.status.lower() in NON_BLOCKING_STATUSES

    def has_upcoming_checkin(self, days: int = 7, reference_date: date | None = None) -> bool:
        """Devuelve True si el check-in es en los próximos *days* días."""
        today = reference_date or date.today()
        return today <= self.check_in <= today + timedelta(days=days)

    def has_upcoming_checkout(self, days: int = 7, reference_date: date | None = None) -> bool:
        """Devuelve True si el check-out es en los próximos *days* días."""
        today = reference_date or date.today()
        return today <= self.check_out <= today + timedelta(days=days)
