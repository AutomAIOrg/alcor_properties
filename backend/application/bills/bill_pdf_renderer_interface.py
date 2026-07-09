"""
Puerto (interfaz) para la generación del PDF de una factura.

La capa de aplicación depende de esta abstracción; la implementación concreta
(Chromium headless) vive en infrastructure/documents.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class BillPdfData:
    """
    Datos de negocio necesarios para renderizar el recibo de una factura.

    Son los mismos que consume la previsualización del front (BillReceiptData); el
    renderer los transforma en las etiquetas ya formateadas de la plantilla.
    """

    bill_id: int
    # Fecha de emisión del recibo. En el flujo de creación es el día en que se genera.
    emission_date: date
    cleaning_date: date
    apartment_id: str
    address: str | None
    cleaning_type_name: str | None
    clean_hours: Decimal
    hourly_rate: Decimal | None
    cost: Decimal
    # True si la factura está pagada (activa sello PAGADA, banda verde, etc.).
    paid: bool
    # Fecha de pago; None si no está pagada.
    paid_at: date | None
    # Frases "Pago confirmado por ... el día ..." ya formateadas (vacío en "Creada").
    paid_confirmations: tuple[str, ...] = field(default_factory=tuple)


class IBillPdfRenderer(ABC):
    """Puerto para generar el contenido binario (PDF) del recibo de una factura."""

    @abstractmethod
    def render(self, data: BillPdfData) -> bytes:
        """
        Genera el PDF de la factura a partir de los datos de negocio.

        Excepciones:
            BillDocumentRenderError: si la generación falla (plantilla o Chromium).
        """
        raise NotImplementedError
