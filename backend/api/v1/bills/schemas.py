"""
DTOs (Data Transfer Objects) para la API de facturas.
"""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field


class BillCreateRequest(BaseModel):
    """
    DTO de entrada para POST /bills/.

    Solo se capturan los datos de la limpieza; el apartamento, las horas, el coste
    y el estado se derivan en el backend a partir de la reserva y del tipo de limpieza.
    """

    record_id: int = Field(..., description="ID de la reserva (booking) asociada a la limpieza")
    cleaning_date: date = Field(..., description="Fecha en la que se realizó la limpieza")
    start_time: time = Field(..., description="Hora de inicio de la limpieza")
    end_time: time = Field(..., description="Hora de fin de la limpieza")
    cleaning_type_id: int = Field(
        ..., description="ID del tipo de limpieza seleccionado; su tarifa determina el coste"
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
    cleaning_type_id: int | None = None
    cleaning_type_name: str | None = None
    state: str
    paid_at: date | None = None
    paid_confirmed_by_admin: datetime | None = None
    paid_confirmed_by_admin_name: str | None = None
    paid_confirmed_by_cleaner: datetime | None = None
    paid_confirmed_by_cleaner_name: str | None = None
    cancellation_note: str | None = None
    previously_cancelled: bool = False
    address: str | None = None
    apartment_description: str | None = None
    created_at: date | None = None


class BillRectifyRequest(BaseModel):
    """
    DTO de entrada para PUT /bills/{bill_id}/rectify.

    Corrige los datos de una factura "Creada" (fecha, horas y tipo de limpieza). La
    tarifa/hora y el coste se recalculan en el backend a partir del tipo elegido; la
    factura permanece en estado "Creada".
    """

    cleaning_date: date = Field(..., description="Nueva fecha de la limpieza facturada")
    clean_hours: float = Field(..., gt=0, description="Nuevas horas de limpieza (mayor que cero)")
    cleaning_type_id: int = Field(
        ..., description="Nuevo tipo de limpieza; su tarifa recalcula el coste"
    )


class BillUpdateStateRequest(BaseModel):
    """DTO de entrada para PUT /bills/{bill_id}. Cambia el estado de una factura."""

    state: str = Field(..., description="Nuevo estado (Creada, Pagada, Cancelada)")
    paid_at: date | None = Field(
        default=None,
        description=(
            "Fecha de pago. Solo la tiene en cuenta la confirmación de la limpiadora "
            "(por defecto, hoy); la confirmación de administración la ignora."
        ),
    )
    cancellation_note: str | None = Field(
        default=None,
        max_length=500,
        description="Nota explicativa. Solo aplica al pasar a 'Cancelada'.",
    )
