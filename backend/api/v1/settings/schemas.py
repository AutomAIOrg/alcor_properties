"""
DTOs (Data Transfer Objects) para la API de ajustes globales.
"""

from pydantic import BaseModel, Field


class BannerSettingResponse(BaseModel):
    """DTO de salida con el estado del banner de avisos."""

    enabled: bool = Field(..., description="Si el banner de avisos está activado globalmente")


class BannerSettingUpdateRequest(BaseModel):
    """DTO de entrada para PUT /settings/banner."""

    enabled: bool = Field(..., description="Nuevo estado del banner (activado/desactivado)")
