from datetime import date

from pydantic import BaseModel, Field, model_validator


class ApartmentSearchFilters(BaseModel):
    """
    Filtros de búsqueda para apartamentos.

    Permite:
    - buscar por cualquier campo relevante de la tabla Apartamentos
    - filtrar por características numéricas
    - filtrar por disponibilidad entre fechas
    """

    # Búqueda libre
    q: str | None = Field(
        default=None,
        description="Término de búsqueda libre aplicado a varios campos del apartamento"
        )

    # Campos de texto de la tabla Apartamentos
    booking_id: str | None = Field(
        default=None,
        description="Filtra por ID (booking_id) del apartamento"
    )

    community: str | None = Field(
        default=None,
        description="Filtra por comunidad del apartamento"
    )

    booking_name: str | None = Field(
        default=None,
        description="Filtra por nombre de reserva del apartamento"
    )

    address: str | None = Field(
        default=None,
        description="Filtra por dirección del apartamento"
    )

    parking: str | None = Field(
        default=None,
        description="Filtra por identificador de parking"
    )

    owner_name: str | None = Field(
        default=None,
        description="Filtra por nombre del propietario del apartamento"
    )
    email: str | None = Field(
        default=None,
        description="Filtra por email del propietario del apartamento"
    )
    phone: str | None = Field(
        default=None,
        description="Filtra por teléfono del propietario del apartamento"
    )

    # Campos numéricos de la tabla Apartamentos
    min_rooms: int | None = Field(
        default=None,
        ge=0,
        description="Filtra por número mínimo de habitaciones"
    )

    max_rooms: int | None = Field(
        default=None,
        ge=0,
        description="Filtra por número máximo de habitaciones"
    )

    min_bathrooms: int | None = Field(
        default=None,
        ge=0,
        description="Filtra por número mínimo de baños"
    )
    max_bathrooms: int | None = Field(
        default=None,
        ge=0,
        description="Filtra por número máximo de baños"
    )

    min_occupants: int | None = Field(
        default=None,
        ge=0,
        description="Filtra por número mínimo de ocupantes"
    )
    max_occupants: int | None = Field(
        default=None,
        ge=0,
        description="Filtra por número máximo de ocupantes"
    )

    available_from: date | None = Field(
        default=None,
        description="Filtra por fecha de disponibilidad desde"
    )

    available_to: date | None = Field(
        default=None,
        description="Filtra por fecha de disponibilidad hasta"
    )

    @model_validator(mode="after")
    def validate_ranges(self):
        if (
            self.min_rooms is not None
            and self.max_rooms is not None
            and self.min_rooms > self.max_rooms
        ):
            raise ValueError("min_rooms no puede ser mayor que max_rooms")

        if (
            self.min_bathrooms is not None
            and self.max_bathrooms is not None
            and self.min_bathrooms > self.max_bathrooms
        ):
            raise ValueError("min_bathrooms no puede ser mayor que max_bathrooms")

        if (
            self.min_occupants is not None
            and self.max_occupants is not None
            and self.min_occupants > self.max_occupants
        ):
            raise ValueError("min_occupants no puede ser mayor que max_occupants")

        if (self.available_from is None) != (self.available_to is None):
            raise ValueError("available_from y available_to deben informarse juntas")

        if (
            self.available_from is not None
            and self.available_to is not None
            and self.available_from >= self.available_to
        ):
            raise ValueError("available_to debe ser posterior a available_from")

        return self
