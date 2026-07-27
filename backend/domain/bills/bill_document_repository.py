"""
Interfaz abstracta de repositorio para documentos de factura.
"""

from abc import ABC, abstractmethod
from datetime import datetime

from domain.bills.bill_document import BillDocument


class IBillDocumentRepository(ABC):
    """Puerto para las operaciones de persistencia de documentos de factura."""

    @abstractmethod
    def create(self, document: BillDocument) -> BillDocument:
        """
        Persiste un nuevo documento y lo devuelve con el *id* asignado.

        La entidad recibida debe tener ``id=None``.
        """
        pass

    @abstractmethod
    def list_by_bill_id(self, bill_id: int) -> list[BillDocument]:
        """Devuelve todos los documentos asociados a una factura."""
        pass

    @abstractmethod
    def get_by_bill_id(self, bill_id: int) -> BillDocument | None:
        """Devuelve el documento asociado a una factura, si existe."""
        pass

    @abstractmethod
    def update(self, document: BillDocument) -> BillDocument:
        """
        Actualiza los metadatos de un documento existente.

        La entidad recibida debe tener ``id`` asignado.
        """
        pass

    @abstractmethod
    def list_retryable(
        self,
        now: datetime,
        limit: int = 100,
        *,
        stale_processing_before: datetime | None = None,
    ) -> list[BillDocument]:
        """
        Devuelve documentos pendientes de sincronización que ya pueden reintentarse.

        Incluye ``Pendiente``/``Error`` con ``next_retry_at`` nulo o vencido, y
        opcionalmente ``Procesando`` cuyo ``uploaded_at`` es anterior a
        ``stale_processing_before`` (intentos cortados a mitad de camino).
        """
        pass
