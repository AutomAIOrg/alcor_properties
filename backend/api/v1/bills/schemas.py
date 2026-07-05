"""
DTOs (Data Transfer Objects) para la API de facturas.
"""

from datetime import date, time
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BillCreateRequest(BaseModel):
    """
    DTO de entrada para POST /bills/.

    Solo se capturan los datos de la limpieza; el apartamento, las horas, el coste
    y el estado se derivan en el backend a partir de la reserva.
    """

    record_id: int = Field(..., description="ID de la reserva (booking) asociada a la limpieza")
    cleaning_date: date = Field(..., description="Fecha en la que se realizó la limpieza")
    start_time: time = Field(..., description="Hora de inicio de la limpieza")
    end_time: time = Field(..., description="Hora de fin de la limpieza")
    hourly_rate: Decimal | None = Field(
        default=None,
        ge=0,
        description="Precio por hora (€). Si no se indica, se usa el del sistema.",
    )


class BillResponse(BaseModel):
    """DTO de salida. Modelo de respuesta para la API."""

    model_config = ConfigDict(from_attributes=True)

    bill_id: int | None = None
    record_id: int | None = None
    apartment_id: str
    cleaning_date: date | None = None
    clean_hours: float
    cost: float | None = None
    hourly_rate: float | None = None
    state: str
    paid_at: date | None = None
    cancellation_note: str | None = None
    previously_cancelled: bool = False


class BillUpdateStateRequest(BaseModel):
    """DTO de entrada para PUT /bills/{bill_id}. Cambia el estado de una factura."""

    state: str = Field(..., description="Nuevo estado (Creada, Pagada, Cancelada)")
    paid_at: date | None = Field(
        default=None,
        description="Fecha de pago. Solo aplica al pasar a 'Pagada'; por defecto, hoy.",
    )
    cancellation_note: str | None = Field(
        default=None,
        max_length=500,
        description="Nota explicativa. Solo aplica al pasar a 'Cancelada'.",
    )
