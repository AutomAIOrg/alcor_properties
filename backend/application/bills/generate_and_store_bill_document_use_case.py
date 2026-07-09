"""
Caso de uso: generar documento PDF de factura y almacenarlo en NAS.
"""

import logging
from datetime import UTC, datetime

from application.bills.bill_pdf_renderer_interface import BillPdfData, IBillPdfRenderer
from application.shared.file_storage_interface import IFileStorage
from domain.bills.bill_document import BillDocument
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.entity import Bill
from domain.bills.repository import IBillRepository
from domain.exceptions import (
    BillDocumentAlreadyExistsError,
    DomainValidationError,
    FileStorageError,
)

logger = logging.getLogger(__name__)

_CONTENT_TYPE_PDF = "application/pdf"


class GenerateAndStoreBillDocumentUseCase:
    """
    Orquesta la generación del PDF de factura (vía renderer) y su subida al NAS.

    Los datos del documento se derivan de la factura persistida.
    La generación real del PDF se delega en IBillPdfRenderer.
    """

    def __init__(
        self,
        bill_repository: IBillRepository,
        document_repository: IBillDocumentRepository,
        pdf_renderer: IBillPdfRenderer,
        file_storage: IFileStorage,
        nas_base_path: str,
    ) -> None:
        self._bill_repository = bill_repository
        self._document_repository = document_repository
        self._pdf_renderer = pdf_renderer
        self._file_storage = file_storage
        self._nas_base_path = nas_base_path.rstrip("/")

    def execute(self, bill_id: int, uploaded_by: int) -> BillDocument:
        bill = self._bill_repository.get_by_id(bill_id)
        self._validate_bill_for_document(bill)

        if self._document_repository.list_by_bill_id(bill_id):
            raise BillDocumentAlreadyExistsError(bill_id)

        assert bill.cleaning_date is not None
        assert bill.hourly_rate is not None

        pdf_data = BillPdfData(
            bill_id=bill_id,
            cleaning_date=bill.cleaning_date,
            apartment_id=bill.apartment_id,
            clean_hours=bill.clean_hours,
            hourly_rate=bill.hourly_rate,
        )
        content = self._pdf_renderer.render(pdf_data)

        remote_folder = (
            f"{self._nas_base_path}/{bill.apartment_id} LIMPIEZAS/{bill.cleaning_date.year}"
        )
        filename = self._build_filename(bill.apartment_id, bill.cleaning_date)

        try:
            nas_path = self._file_storage.upload_bytes(
                remote_folder=remote_folder,
                filename=filename,
                content=content,
                content_type=_CONTENT_TYPE_PDF,
            )
        except FileStorageError:
            raise
        except Exception as exc:
            logger.exception("Error inesperado al subir documento de factura %s al NAS", bill_id)
            raise FileStorageError(
                "No se pudo almacenar el documento de factura en el NAS."
            ) from exc

        document = BillDocument(
            bill_id=bill_id,
            filename=filename,
            nas_path=nas_path,
            content_type=_CONTENT_TYPE_PDF,
            size_bytes=len(content),
            uploaded_by=uploaded_by,
            uploaded_at=datetime.now(UTC),
        )

        try:
            return self._document_repository.create(document)
        except BillDocumentAlreadyExistsError:
            self._compensate_upload(nas_path)
            raise
        except Exception as exc:
            self._compensate_upload(nas_path)
            logger.error(
                "Documento subido al NAS (%s) pero falló la persistencia en BD para factura %s",
                nas_path,
                bill_id,
            )
            raise FileStorageError(
                "El documento se subió al NAS pero no se pudo registrar en la base de datos."
            ) from exc

    def _compensate_upload(self, nas_path: str) -> None:
        try:
            self._file_storage.delete(nas_path)
        except Exception:
            logger.exception("No se pudo eliminar el archivo huérfano en NAS: %s", nas_path)

    @staticmethod
    def _validate_bill_for_document(bill: Bill) -> None:
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

    @staticmethod
    def _build_filename(apartment_id: str, cleaning_date) -> str:
        date_str = cleaning_date.strftime("%d.%m.%Y")
        return f"{apartment_id} LIMPIEZA {date_str}.pdf"
