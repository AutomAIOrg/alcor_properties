"""
Entidad de dominio de tipo de limpieza.

Un tipo de limpieza (p. ej. "Limpieza normal", "Limpieza fin de semana") define la
tarifa por hora que se aplica al facturar una limpieza de esa clase. Al generar una
factura se selecciona el tipo y su tarifa determina el coste (horas × tarifa).
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CleaningType(BaseModel):
    """
    Entidad de dominio que representa qué es un tipo de limpieza.

    Invariantes de negocio aplicadas aquí:
    - Nombre no vacío (identifica el tipo de cara al usuario).
    - Tarifa por hora no negativa.
    """

    model_config = ConfigDict(frozen=True)

    cleaning_type_id: int | None = Field(
        default=None,
        description="Clave primaria de base de datos. None para tipos aún no persistidos.",
    )
    name: str = Field(..., description="Nombre único del tipo de limpieza")
    hourly_rate: Decimal = Field(
        ..., ge=0, description="Precio por hora de limpieza aplicado a este tipo (€)"
    )
    active: bool = Field(
        default=True,
        description="Si es False, el tipo no puede seleccionarse al crear nuevas facturas",
    )

    # ------------------------------------------------------------------ #
    # Validadores                                                        #
    # ------------------------------------------------------------------ #

    @field_validator("name")
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre del tipo de limpieza no puede estar vacío")
        return v.strip()
