"""
Interfaz abstracta de repositorio para documentos de factura.
"""

from abc import ABC, abstractmethod

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
