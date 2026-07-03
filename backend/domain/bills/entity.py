"""
Entidad de dominio de factura.

Una factura representa la limpieza realizada en un apartamento tras una reserva.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

# Estados de una factura.
# "Pendiente" es un estado virtual (limpieza facturable que aún no tiene registro);
# los demás corresponden a facturas ya persistidas.
BILL_STATE_PENDING = "Pendiente"
BILL_STATE_CREATED = "Creada"
BILL_STATE_PAID = "Pagada"
BILL_STATE_CANCELLED = "Cancelada"

# Transiciones de estado permitidas entre facturas reales (Pendiente queda fuera al ser virtual).
ALLOWED_BILL_TRANSITIONS: dict[str, set[str]] = {
    BILL_STATE_CREATED: {BILL_STATE_PAID, BILL_STATE_CANCELLED},
    BILL_STATE_PAID: {BILL_STATE_CREATED},
    BILL_STATE_CANCELLED: {BILL_STATE_CREATED},
}


class Bill(BaseModel):
    """
    Entidad de dominio que representa qué es una factura.

    Invariantes de negocio aplicadas aquí:
    - Identificador único (bill_id), asignado por la base de datos al persistir.
    """

    model_config = ConfigDict(frozen=True)

    bill_id: int | None = Field(
        default=None,
        description="Clave primaria de base de datos. None para facturas aún no persistidas.",
    )

    record_id: int | None = Field(
        default=None,
        description="ID de la reserva (booking) asociada a la factura.",
    )
    cleaning_date: date | None = Field(
        default=None, description="Fecha de la limpieza facturada (ISO 8601)"
    )
    clean_hours: Decimal = Field(
        default=Decimal(0),
        ge=0,
        description="Número de horas de limpieza (admite fracciones, ej. 1.5)",
    )
    cost: Decimal | None = Field(default=None, ge=0, description="Coste de la limpieza facturada")
    apartment_id: str = Field(
        ..., description="Identificador único del apartamento asociado a la factura"
    )
    state: str = Field(
        default=BILL_STATE_CREATED,
        description="Estado de la factura (Pendiente, Creada, Pagada, Cancelada)",
    )
    hourly_rate: Decimal | None = Field(
        default=None, ge=0, description="Precio por hora de limpieza aplicado en esta factura (€)"
    )
    cleaning_type_id: int | None = Field(
        default=None, description="ID del tipo de limpieza aplicado (catálogo)"
    )
    cleaning_type_name: str | None = Field(
        default=None,
        description="Nombre del tipo de limpieza congelado al facturar (histórico estable)",
    )
    paid_at: date | None = Field(
        default=None, description="Fecha en la que se pagó la factura (solo si está Pagada)"
    )

    # Campo calculado — establecido por la capa de aplicación, no persistido en la BD.
    # True en una factura virtual 'Pendiente' cuya limpieza tuvo una factura cancelada
    # (puede volver a facturarse). Permite a la UI indicar "Factura cancelada".
    previously_cancelled: bool = Field(
        default=False,
        description="True si la limpieza tuvo una factura cancelada y puede volver a facturarse",
    )
