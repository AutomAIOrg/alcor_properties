"""
DTOs para la API de configuración.
"""

from decimal import Decimal

from pydantic import BaseModel, Field


class CleaningRateResponse(BaseModel):
    """Precio por hora de limpieza vigente."""

    cleaning_hourly_rate: float


class CleaningRateUpdateRequest(BaseModel):
    """DTO de entrada para actualizar el precio por hora de limpieza."""

    cleaning_hourly_rate: Decimal = Field(..., ge=0, description="Precio por hora de limpieza (€)")
