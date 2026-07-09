"""
Caso de uso: generar el PDF del recibo de una factura y guardarlo.

Por ahora el PDF se escribe en una carpeta local (bill_templates); la configuración del
NAS y el ciclo de vida del documento se abordarán más adelante. La generación del PDF real
se delega en IBillPdfRenderer.
"""

import logging
from datetime import date
from pathlib import Path

from application.bills.bill_pdf_renderer_interface import (
    BillPdfData,
    IBillPdfRenderer,
    PaidConfirmation,
)
from domain.apartments.repository import IApartmentRepository
from domain.bills.entity import BILL_STATE_PAID, Bill
from domain.exceptions import DomainValidationError

logger = logging.getLogger(__name__)


class GenerateBillDocumentUseCase:
    """
    Genera el recibo PDF de una factura ya persistida y lo guarda en disco.

    La dirección del apartamento (que la factura no almacena) se resuelve desde el
    repositorio de apartamentos en el momento de generar.
    """

    def __init__(
        self,
        apartment_repository: IApartmentRepository,
        pdf_renderer: IBillPdfRenderer,
        output_dir: str | Path,
    ) -> None:
        self._apartment_repository = apartment_repository
        self._pdf_renderer = pdf_renderer
        self._output_dir = Path(output_dir)

    def execute(self, bill: Bill) -> Path:
        if bill.bill_id is None or bill.cleaning_date is None or bill.cost is None:
            raise DomainValidationError(
                "La factura no tiene datos suficientes para generar el PDF."
            )

        apartment = self._apartment_repository.get_by_apartment_id(bill.apartment_id)
        address = apartment.address if apartment is not None else None

        data = BillPdfData(
            bill_id=bill.bill_id,
            # Emisión = fecha de creación congelada (para que la FECHA del recibo no cambie
            # al regenerarlo al pagar); solo se recurre a hoy si la factura no la tiene.
            emission_date=bill.created_at or date.today(),
            cleaning_date=bill.cleaning_date,
            apartment_id=bill.apartment_id,
            address=address,
            cleaning_type_name=bill.cleaning_type_name,
            clean_hours=bill.clean_hours,
            hourly_rate=bill.hourly_rate,
            cost=bill.cost,
            paid=bill.state == BILL_STATE_PAID,
            paid_at=bill.paid_at,
            paid_confirmations=self._paid_confirmations(bill),
        )

        content = self._pdf_renderer.render(data)

        self._output_dir.mkdir(parents=True, exist_ok=True)
        output_path = self._output_dir / self._filename(bill)
        output_path.write_bytes(content)

        logger.info("PDF de la factura %s generado en %s", bill.bill_id, output_path)
        return output_path

    @staticmethod
    def _paid_confirmations(bill: Bill) -> tuple[PaidConfirmation, ...]:
        """
        Confirmaciones de pago registradas (administración y/o limpiadora, en ese orden).
        Port de format-confirmation.ts::paidConfirmationsOf.
        """
        confirmations: list[PaidConfirmation] = []
        if bill.paid_confirmed_by_admin and bill.paid_confirmed_by_admin_name:
            confirmations.append(
                PaidConfirmation(bill.paid_confirmed_by_admin_name, bill.paid_confirmed_by_admin)
            )
        if bill.paid_confirmed_by_cleaner and bill.paid_confirmed_by_cleaner_name:
            confirmations.append(
                PaidConfirmation(
                    bill.paid_confirmed_by_cleaner_name, bill.paid_confirmed_by_cleaner
                )
            )
        return tuple(confirmations)

    @staticmethod
    def _filename(bill: Bill) -> str:
        date_part = bill.cleaning_date.strftime("%Y%m%d") if bill.cleaning_date else "sinfecha"
        return f"factura_{bill.bill_id}_{bill.apartment_id}_{date_part}.pdf"
