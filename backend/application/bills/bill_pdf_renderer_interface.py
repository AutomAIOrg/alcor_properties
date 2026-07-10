"""
Interfaz abstracta para la generación de PDFs de factura.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class BillPdfData:
    """Datos de negocio necesarios para renderizar una factura PDF."""

    bill_id: int
    cleaning_date: date
    apartment_id: str
    clean_hours: Decimal
    hourly_rate: Decimal

    @property
    def total_cost(self) -> Decimal:
        return (self.clean_hours * self.hourly_rate).quantize(Decimal("0.01"))


class IBillPdfRenderer(ABC):
    """Puerto para generar el contenido binario de una factura PDF."""

    @abstractmethod
    def render(self, data: BillPdfData) -> bytes:
        """
        Genera el PDF de factura a partir de los datos de negocio.

        Raises:
            BillDocumentRenderError: si la generación falla.
        """
        pass
