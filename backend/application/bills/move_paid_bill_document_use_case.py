"""
Caso de uso: mover documento PDF de factura pagada de pendientes a pagadas en NAS.
"""

import logging
from datetime import UTC, datetime, timedelta

from application.bills.bill_document_helpers import (
    CONTENT_TYPE_PDF,
    build_bill_document_filename,
    build_bill_pdf_data,
    paid_invoices_folder,
    validate_bill_for_document,
)
from application.bills.bill_pdf_renderer_interface import IBillPdfRenderer
from application.shared.file_storage_interface import IFileStorage
from domain.bills.bill_document import (
    BILL_DOCUMENT_OPERATION_MOVE_TO_PAID,
    BILL_DOCUMENT_STATUS_COMPLETED,
    BILL_DOCUMENT_STATUS_ERROR,
    BillDocument,
)
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.repository import IBillRepository
from domain.exceptions import FileStorageError

logger = logging.getLogger(__name__)


class MovePaidBillDocumentUseCase:
    """
    Genera el PDF de una factura pagada, lo sube a ``1FACTURAS PAGADAS`` y elimina
    el archivo previo de ``1FACTURAS PENDIENTE`` si existía.
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
        validate_bill_for_document(bill)

        existing_documents = self._document_repository.list_by_bill_id(bill_id)
        existing_document = existing_documents[0] if existing_documents else None
        old_nas_path = existing_document.nas_path if existing_document else None

        assert bill.cleaning_date is not None
        filename = build_bill_document_filename(bill.apartment_id, bill.cleaning_date)
        remote_folder = paid_invoices_folder(self._nas_base_path)
        now = datetime.now(UTC)

        try:
            pdf_data = build_bill_pdf_data(bill, bill_id)
            content = self._pdf_renderer.render(pdf_data)
            new_nas_path = self._file_storage.upload_bytes(
                remote_folder=remote_folder,
                filename=filename,
                content=content,
                content_type=CONTENT_TYPE_PDF,
            )
            document = BillDocument(
                id=existing_document.id if existing_document else None,
                bill_id=bill_id,
                filename=filename,
                nas_path=new_nas_path,
                content_type=CONTENT_TYPE_PDF,
                size_bytes=len(content),
                uploaded_by=uploaded_by,
                uploaded_at=now,
                status=BILL_DOCUMENT_STATUS_COMPLETED,
                operation=BILL_DOCUMENT_OPERATION_MOVE_TO_PAID,
                attempts=(existing_document.attempts if existing_document else 0) + 1,
                completed_at=now,
                previous_nas_path=old_nas_path,
            )
        except FileStorageError:
            failed = self._failed_document(
                existing_document=existing_document,
                bill_id=bill_id,
                filename=filename,
                nas_path=f"{remote_folder}/{filename}",
                uploaded_by=uploaded_by,
                uploaded_at=now,
                old_nas_path=old_nas_path,
                error="No se pudo almacenar el documento de factura pagada en el NAS.",
            )
            return self._persist_failed(failed)
        except Exception as exc:
            logger.exception(
                "Error inesperado al subir documento pagado de factura %s al NAS", bill_id
            )
            failed = self._failed_document(
                existing_document=existing_document,
                bill_id=bill_id,
                filename=filename,
                nas_path=f"{remote_folder}/{filename}",
                uploaded_by=uploaded_by,
                uploaded_at=now,
                old_nas_path=old_nas_path,
                error=str(exc),
            )
            return self._persist_failed(failed)

        try:
            if existing_document is not None:
                persisted = self._document_repository.update(document)
            else:
                persisted = self._document_repository.create(document)
        except Exception as exc:
            self._compensate_upload(document.nas_path)
            logger.error(
                "Documento pagado subido al NAS (%s) pero falló la persistencia en BD "
                "para factura %s",
                document.nas_path,
                bill_id,
            )
            raise FileStorageError(
                "El documento se subió al NAS pero no se pudo registrar en la base de datos."
            ) from exc

        if old_nas_path and old_nas_path != new_nas_path:
            try:
                self._file_storage.delete(old_nas_path)
            except Exception as exc:
                logger.exception(
                    "No se pudo eliminar el documento pendiente %s tras pagar factura %s",
                    old_nas_path,
                    bill_id,
                )
                retryable = persisted.model_copy(
                    update={
                        "status": BILL_DOCUMENT_STATUS_ERROR,
                        "operation": BILL_DOCUMENT_OPERATION_MOVE_TO_PAID,
                        "last_error": str(exc)[:1000],
                        "next_retry_at": datetime.now(UTC) + timedelta(hours=1),
                        "completed_at": None,
                        "previous_nas_path": old_nas_path,
                    }
                )
                return self._document_repository.update(retryable)

        return persisted

    def _persist_failed(self, document: BillDocument) -> BillDocument:
        if document.id is None:
            return self._document_repository.create(document)
        return self._document_repository.update(document)

    @staticmethod
    def _failed_document(
        *,
        existing_document: BillDocument | None,
        bill_id: int,
        filename: str,
        nas_path: str,
        uploaded_by: int,
        uploaded_at: datetime,
        old_nas_path: str | None,
        error: str,
    ) -> BillDocument:
        return BillDocument(
            id=existing_document.id if existing_document else None,
            bill_id=bill_id,
            filename=filename,
            nas_path=existing_document.nas_path if existing_document else nas_path,
            content_type=CONTENT_TYPE_PDF,
            size_bytes=existing_document.size_bytes if existing_document else 0,
            uploaded_by=uploaded_by,
            uploaded_at=uploaded_at,
            status=BILL_DOCUMENT_STATUS_ERROR,
            operation=BILL_DOCUMENT_OPERATION_MOVE_TO_PAID,
            attempts=(existing_document.attempts if existing_document else 0) + 1,
            last_error=error[:1000],
            next_retry_at=uploaded_at + timedelta(hours=1),
            completed_at=None,
            previous_nas_path=old_nas_path,
        )

    def _compensate_upload(self, nas_path: str) -> None:
        try:
            self._file_storage.delete(nas_path)
        except Exception:
            logger.exception("No se pudo eliminar el archivo huérfano en NAS: %s", nas_path)
