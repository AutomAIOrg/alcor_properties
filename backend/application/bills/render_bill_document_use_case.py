"""
Caso de uso: generar el PDF de una factura para descarga directa.
"""

from dataclasses import dataclass

from application.bills.bill_document_helpers import (
    build_bill_document_filename,
    build_bill_pdf_data,
    validate_bill_for_document,
)
from application.bills.bill_pdf_renderer_interface import IBillPdfRenderer
from domain.apartments.repository import IApartmentRepository
from domain.bills.repository import IBillRepository


@dataclass(frozen=True)
class RenderedBillDocument:
    """Recibo listo para servir por HTTP: nombre de archivo y contenido binario."""

    filename: str
    content: bytes


class RenderBillDocumentUseCase:
    """
    Renderiza el recibo de una factura y devuelve sus bytes, sin pasar por el NAS.

    A diferencia de GenerateAndStoreBillDocumentUseCase, aquí no hay archivado: no se sube
    nada, no se registra estado documental y no hay reintentos. Es una lectura pura, pensada
    para que el usuario descargue la factura desde la aplicación. El PDF se rinde con los
    datos actuales de la factura, así que sale en su versión correcta (pendiente o pagada)
    según el estado —el mismo criterio que aplica el recibo archivado en el NAS—.
    """

    def __init__(
        self,
        bill_repository: IBillRepository,
        apartment_repository: IApartmentRepository,
        pdf_renderer: IBillPdfRenderer,
    ) -> None:
        self._bill_repository = bill_repository
        self._apartment_repository = apartment_repository
        self._pdf_renderer = pdf_renderer

    def execute(self, bill_id: int) -> RenderedBillDocument:
        bill = self._bill_repository.get_by_id(bill_id)
        validate_bill_for_document(bill)

        assert bill.cleaning_date is not None
        pdf_data = build_bill_pdf_data(bill, bill_id, self._apartment_repository)
        return RenderedBillDocument(
            filename=build_bill_document_filename(bill.apartment_id, bill.cleaning_date),
            content=self._pdf_renderer.render(pdf_data),
        )
