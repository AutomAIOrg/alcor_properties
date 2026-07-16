"""
Entidad de dominio de apartamento
"""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Color personalizado del calendario: hexadecimal #RRGGBB.
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Importe por noche del cupo eléctrico aplicado a los apartamentos que lo tienen
# activado. Es solo el valor inicial: cada apartamento guarda su propia tarifa y el
# administrador puede cambiarla desde la gestión de apartamentos.
DEFAULT_ELECTRIC_ALLOWANCE_RATE = 4.0


class Apartment(BaseModel):
    """
    Entidad de dominio que representa qué es un apartamento.

    Invariantes de negocio aplicadas aquí:
    - Identificador único (apartment_id)
    """

    model_config = ConfigDict(frozen=True)

    apartment_id: str = Field(..., description="Identificador único del apartamento (ej. A123)")
    community: str | None = Field(
        default=None, description="Comunidad a la que pertenece el apartamento"
    )
    apartment_description: str | None = Field(
        default=None, description="Descripción del apartamento en la plataforma de reservas"
    )
    address: str | None = Field(default=None, description="Dirección del apartamento")
    rooms: int = Field(default=0, ge=0, description="Número de habitaciones del apartamento")
    bathrooms: int = Field(default=0, ge=0, description="Número de baños del apartamento")
    parking: str = Field(
        default="N/A", description="Número de la plaza del parking del apartamento"
    )
    total_occupants: int = Field(
        default=0, ge=0, description="Número total de ocupantes permitidos en el apartamento"
    )
    owner_name: str | None = Field(
        default=None, description="Nombre del propietario del apartamento"
    )
    email: str | None = Field(
        default=None, description="Correo electrónico del propietario del apartamento"
    )
    phone: str | None = Field(default=None, description="Teléfono del propietario del apartamento")
    color: str | None = Field(
        default=None,
        description="Color personalizado del apartamento en el calendario (hexadecimal #RRGGBB). "
        "Si es None se usa el color automático.",
    )
    electric_allowance_enabled: bool = Field(
        default=False,
        description="Si el apartamento aplica cupo eléctrico a sus reservas",
    )
    electric_allowance_rate: float = Field(
        default=DEFAULT_ELECTRIC_ALLOWANCE_RATE,
        ge=0,
        description="Importe por noche del cupo eléctrico. Solo se aplica si "
        "electric_allowance_enabled es True.",
    )

    # ------------------------------------------------------------------ #
    # Validadores                                                        #
    # ------------------------------------------------------------------ #

    @field_validator("apartment_id")
    def validate_apartment_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("apartment_id no puede estar vacío")
        return v.strip()

    @field_validator("color")
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not HEX_COLOR_PATTERN.match(v):
            raise ValueError("color debe tener formato hexadecimal #RRGGBB")
        return v
