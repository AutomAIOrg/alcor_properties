"""
DTOs (Data Transfer Objects) para la API de tipos de limpieza.
"""

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CleaningTypeResponse(BaseModel):
    """DTO de salida. Modelo de respuesta para la API."""

    model_config = ConfigDict(from_attributes=True)

    cleaning_type_id: int
    name: str
    hourly_rate: float
    active: bool


class CleaningTypeCreateRequest(BaseModel):
    """DTO de entrada para POST /cleaning-types/."""

    name: str = Field(..., max_length=100, description="Nombre único del tipo de limpieza")
    hourly_rate: Decimal = Field(..., ge=0, description="Precio por hora de limpieza (€)")
    active: bool = Field(default=True, description="Si el tipo puede usarse al facturar")


class CleaningTypeUpdateRequest(BaseModel):
    """DTO de entrada para PUT /cleaning-types/{cleaning_type_id}."""

    name: str = Field(..., max_length=100, description="Nombre único del tipo de limpieza")
    hourly_rate: Decimal = Field(..., ge=0, description="Precio por hora de limpieza (€)")
    active: bool = Field(..., description="Si el tipo puede usarse al facturar")
