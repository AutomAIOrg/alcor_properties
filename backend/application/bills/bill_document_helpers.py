"""
Utilidades compartidas para generación y movimiento de documentos de factura en NAS.
"""

from application.bills.bill_pdf_renderer_interface import BillPdfData
from domain.bills.entity import Bill
from domain.exceptions import DomainValidationError

CONTENT_TYPE_PDF = "application/pdf"
PENDING_INVOICES_FOLDER = "1FACTURAS PENDIENTE"
PAID_INVOICES_FOLDER = "1FACTURAS PAGADAS"


def pending_invoices_folder(nas_base_path: str) -> str:
    return f"{nas_base_path.rstrip('/')}/{PENDING_INVOICES_FOLDER}"


def paid_invoices_folder(nas_base_path: str) -> str:
    return f"{nas_base_path.rstrip('/')}/{PAID_INVOICES_FOLDER}"


def build_bill_pdf_data(bill: Bill, bill_id: int) -> BillPdfData:
    assert bill.cleaning_date is not None
    assert bill.hourly_rate is not None
    return BillPdfData(
        bill_id=bill_id,
        cleaning_date=bill.cleaning_date,
        apartment_id=bill.apartment_id,
        clean_hours=bill.clean_hours,
        hourly_rate=bill.hourly_rate,
    )


def build_bill_document_filename(apartment_id: str, cleaning_date) -> str:
    date_str = cleaning_date.strftime("%d.%m.%Y")
    return f"{apartment_id} LIMPIEZA {date_str}.pdf"


def validate_bill_for_document(bill: Bill) -> None:
    if bill.cleaning_date is None:
        raise DomainValidationError(
            "La factura no tiene fecha de limpieza; no se puede generar el documento."
        )
    if bill.clean_hours <= 0:
        raise DomainValidationError(
            "La factura no tiene horas de limpieza válidas; no se puede generar el documento."
        )
    if bill.hourly_rate is None:
        raise DomainValidationError(
            "La factura no tiene tarifa por hora; no se puede generar el documento."
        )
    if bill.hourly_rate < 0:
        raise DomainValidationError("La tarifa por hora no puede ser negativa.")
    if not bill.apartment_id.strip():
        raise DomainValidationError("El apartamento es obligatorio.")
