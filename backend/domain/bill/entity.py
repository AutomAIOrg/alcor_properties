"""
Entidad de domonio de factura
"""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Bill(BaseModel):
    """
    Entidad de dominio que representa qué es una factura.

    Invariantes de negocio aplicadas aquí:
    - Identificador único (bill_id)
    """

    model_config = ConfigDict(frozen=True)

    bill_id: str = Field(..., description="Identificador único de la factura (ej. B123)")

    record_id: int | None = Field(
        default=None,
        description="Número de reserva asociado a la factura. None para facturas aún no persistidas.",
    )
    created_at: date | None = Field(
        default=None, description="Fecha de creación de la factura en formato ISO 8601"
    )
    clean_hours: int = Field(
        default=0, ge=0, description="Número de horas de limpieza asociadas a la factura"
    )
    apartment_id: str = Field(
        ..., description="Identificador único del apartamento asociado a la factura"
    )
    state: str = Field(
        default="Pending", description="Estado de la factura (Pending, Paid, Cancelled)"
    )
