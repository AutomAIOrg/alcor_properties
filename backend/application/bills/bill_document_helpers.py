"""
Utilidades compartidas para generación y movimiento de documentos de factura en NAS.
"""

from datetime import date

from application.bills.bill_pdf_renderer_interface import BillPdfData, PaidConfirmation
from domain.apartments.repository import IApartmentRepository
from domain.bills.entity import BILL_STATE_PAID, Bill
from domain.exceptions import DomainValidationError

CONTENT_TYPE_PDF = "application/pdf"
PENDING_INVOICES_FOLDER = "1FACTURAS PENDIENTE"
PAID_INVOICES_FOLDER = "1FACTURAS PAGADAS"


def pending_invoices_folder(nas_base_path: str) -> str:
    return f"{nas_base_path.rstrip('/')}/{PENDING_INVOICES_FOLDER}"


def paid_invoices_folder(nas_base_path: str) -> str:
    return f"{nas_base_path.rstrip('/')}/{PAID_INVOICES_FOLDER}"


def build_bill_pdf_data(
    bill: Bill,
    bill_id: int,
    apartment_repository: IApartmentRepository,
) -> BillPdfData:
    """
    Construye los datos de negocio del recibo a partir de la factura persistida.

    La dirección del apartamento (que la factura no almacena) se resuelve desde el
    repositorio de apartamentos para que el PDF salga igual que la previsualización del front.
    """
    assert bill.cleaning_date is not None
    assert bill.hourly_rate is not None
    assert bill.cost is not None

    apartment = apartment_repository.get_by_apartment_id(bill.apartment_id)
    address = apartment.address if apartment is not None else None

    return BillPdfData(
        bill_id=bill_id,
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
        paid_confirmations=_paid_confirmations(bill),
    )


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
            PaidConfirmation(bill.paid_confirmed_by_cleaner_name, bill.paid_confirmed_by_cleaner)
        )
    return tuple(confirmations)


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
    if bill.cost is None:
        raise DomainValidationError("La factura no tiene coste; no se puede generar el documento.")
    if not bill.apartment_id.strip():
        raise DomainValidationError("El apartamento es obligatorio.")
