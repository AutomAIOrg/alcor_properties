"""
Entidad de dominio para documentos de factura almacenados en NAS.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BillDocument(BaseModel):
    """Metadatos de un documento PDF de factura generado y subido al NAS."""

    model_config = ConfigDict(frozen=True)

    id: int | None = Field(
        default=None,
        description="Clave primaria. None antes de persistir.",
    )
    bill_id: int = Field(..., description="Factura asociada al documento")
    filename: str = Field(..., description="Nombre del archivo en el NAS")
    nas_path: str = Field(..., description="Ruta completa del archivo en el NAS")
    content_type: str = Field(default="application/pdf", description="Tipo MIME del documento")
    size_bytes: int = Field(..., ge=0, description="Tamaño del archivo en bytes")
    uploaded_by: int = Field(..., description="ID del usuario que generó el documento")
    uploaded_at: datetime = Field(..., description="Fecha y hora de generación/subida (UTC)")
