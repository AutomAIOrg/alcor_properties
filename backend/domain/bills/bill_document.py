"""
Entidad de dominio para documentos de factura almacenados en NAS.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

BILL_DOCUMENT_STATUS_PENDING = "Pendiente"
BILL_DOCUMENT_STATUS_PROCESSING = "Procesando"
BILL_DOCUMENT_STATUS_COMPLETED = "Completado"
BILL_DOCUMENT_STATUS_ERROR = "Error"

BILL_DOCUMENT_OPERATION_GENERATE_PENDING = "GENERATE_PENDING"
BILL_DOCUMENT_OPERATION_MOVE_TO_PAID = "MOVE_TO_PAID"


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
    status: str = Field(
        default=BILL_DOCUMENT_STATUS_PENDING,
        description="Estado de sincronización del documento con el NAS",
    )
    operation: str = Field(
        default=BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
        description="Operación documental pendiente o completada",
    )
    attempts: int = Field(default=0, ge=0, description="Número de intentos de sincronización")
    last_error: str | None = Field(
        default=None,
        description="Último error registrado al sincronizar el documento con el NAS",
    )
    next_retry_at: datetime | None = Field(
        default=None,
        description="Fecha a partir de la cual el worker puede reintentar la operación",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Fecha en la que la sincronización terminó correctamente",
    )
    previous_nas_path: str | None = Field(
        default=None,
        description="Ruta anterior a limpiar en el NAS tras mover el documento",
    )
