"""
Schemas de API para apartamentos
"""

from pydantic import BaseModel, Field


class ApartmentResponse(BaseModel):
    """
    Respuesta HTTP con la información de un apartamento
    """

    apartment_id: str = Field(description="Identificador único del apartamento")
    community: str | None = Field(default=None, description="Comunidad del apartamento")
    apartment_description: str | None = Field(
        default=None, description="Descripción del apartamento en la plataforma de reservas"
    )
    address: str | None = Field(default=None, description="Dirección del apartamento")
    rooms: int = Field(description="Número de habitaciones")
    bathrooms: int = Field(description="Número de baños")
    parking: str = Field(description="Identificador de parking")
    total_occupants: int = Field(description="Número máximo de ocupantes")
    owner_name: str | None = Field(default=None, description="Nombre del propietario")
    email: str | None = Field(default=None, description="Email del propietario")
    phone: str | None = Field(default=None, description="Teléfono del propietario")
