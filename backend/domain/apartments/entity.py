"""
Entidad de dominio de apartamento
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Apartment(BaseModel):
    """
    Entidad de dominio que representa qué es un apartamento.

    Invariantes de negocio aplicadas aquí:
    - Identificador único (booking_id)
    """

    model_config = ConfigDict(frozen=True)

    booking_id: str = Field(..., description="Identificador único del apartamento (ej. A123)")
    community: str | None = Field(
        default=None, description="Comunidad a la que pertenece el apartamento"
    )
    booking_name: str | None = Field(
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

    # ------------------------------------------------------------------ #
    # Validadores                                                        #
    # ------------------------------------------------------------------ #

    @field_validator("booking_id")
    def validate_booking_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("booking_id no puede estar vacío")
        return v.strip()
