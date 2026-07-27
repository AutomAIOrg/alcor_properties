"""
Caso de uso: reintentar sincronizaciones pendientes de documentos de factura con el NAS.
"""

import logging
from datetime import UTC, datetime, timedelta

from application.bills.bill_document_helpers import (
    CONTENT_TYPE_PDF,
    build_bill_document_filename,
    build_bill_pdf_data,
    paid_invoices_folder,
    pending_invoices_folder,
    validate_bill_for_document,
)
from application.bills.bill_pdf_renderer_interface import IBillPdfRenderer
from application.shared.file_storage_interface import IFileStorage
from domain.apartments.repository import IApartmentRepository
from domain.bills.bill_document import (
    BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
    BILL_DOCUMENT_OPERATION_MOVE_TO_PAID,
    BILL_DOCUMENT_STATUS_COMPLETED,
    BILL_DOCUMENT_STATUS_ERROR,
    BILL_DOCUMENT_STATUS_PENDING,
    BillDocument,
)
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.entity import BILL_STATE_PAID, Bill
from domain.bills.repository import IBillRepository

logger = logging.getLogger(__name__)

STALE_PROCESSING_AFTER = timedelta(minutes=15)
_RETRY_DELAY = timedelta(hours=1)


class RetryBillDocumentSyncUseCase:
    """Procesa documentos pendientes de sincronización y facturas huérfanas sin documento."""

    def __init__(
        self,
        bill_repository: IBillRepository,
        document_repository: IBillDocumentRepository,
        apartment_repository: IApartmentRepository,
        pdf_renderer: IBillPdfRenderer,
        file_storage: IFileStorage,
        nas_base_path: str,
    ) -> None:
        self._bill_repository = bill_repository
        self._document_repository = document_repository
        self._apartment_repository = apartment_repository
        self._pdf_renderer = pdf_renderer
        self._file_storage = file_storage
        self._nas_base_path = nas_base_path.rstrip("/")

    def execute(self, limit: int = 100, *, uploaded_by: int) -> list[BillDocument]:
        now = datetime.now(UTC)
        results: list[BillDocument] = []
        remaining = limit

        orphans = self._bill_repository.list_without_documents(limit=remaining)
        for bill in orphans:
            document = self._ensure_orphan_document(bill, uploaded_by=uploaded_by, now=now)
            results.append(self._retry_document(document, now))
            remaining -= 1
            if remaining <= 0:
                return results

        if remaining > 0:
            stale_before = now - STALE_PROCESSING_AFTER
            documents = self._document_repository.list_retryable(
                now,
                limit=remaining,
                stale_processing_before=stale_before,
            )
            results.extend(self._retry_document(document, now) for document in documents)

        return results

    def _ensure_orphan_document(
        self, bill: Bill, *, uploaded_by: int, now: datetime
    ) -> BillDocument:
        assert bill.bill_id is not None
        assert bill.cleaning_date is not None
        validate_bill_for_document(bill)

        operation = (
            BILL_DOCUMENT_OPERATION_MOVE_TO_PAID
            if bill.state == BILL_STATE_PAID
            else BILL_DOCUMENT_OPERATION_GENERATE_PENDING
        )
        folder = self._folder_for_operation(operation)
        filename = build_bill_document_filename(bill.apartment_id, bill.cleaning_date)
        return self._document_repository.create(
            BillDocument(
                bill_id=bill.bill_id,
                filename=filename,
                nas_path=f"{folder}/{filename}",
                content_type=CONTENT_TYPE_PDF,
                size_bytes=0,
                uploaded_by=uploaded_by,
                uploaded_at=now,
                status=BILL_DOCUMENT_STATUS_PENDING,
                operation=operation,
                attempts=0,
                next_retry_at=None,
            )
        )

    def _retry_document(self, document: BillDocument, now: datetime) -> BillDocument:
        try:
            bill = self._bill_repository.get_by_id(document.bill_id)
            validate_bill_for_document(bill)
            assert bill.cleaning_date is not None

            folder = self._folder_for_operation(document.operation)
            filename = build_bill_document_filename(bill.apartment_id, bill.cleaning_date)
            content = self._pdf_renderer.render(
                build_bill_pdf_data(bill, document.bill_id, self._apartment_repository)
            )
            nas_path = self._file_storage.upload_bytes(
                remote_folder=folder,
                filename=filename,
                content=content,
                content_type=CONTENT_TYPE_PDF,
            )
            updated = document.model_copy(
                update={
                    "filename": filename,
                    "nas_path": nas_path,
                    "content_type": CONTENT_TYPE_PDF,
                    "size_bytes": len(content),
                    "uploaded_at": now,
                    "status": BILL_DOCUMENT_STATUS_COMPLETED,
                    "attempts": document.attempts + 1,
                    "last_error": None,
                    "next_retry_at": None,
                    "completed_at": now,
                }
            )
            persisted = self._document_repository.update(updated)
            return self._cleanup_previous_path(persisted, now)
        except Exception as exc:
            logger.exception(
                "Falló el reintento de sincronización documental %s para factura %s",
                document.id,
                document.bill_id,
            )
            return self._document_repository.update(
                document.model_copy(
                    update={
                        "status": BILL_DOCUMENT_STATUS_ERROR,
                        "attempts": document.attempts + 1,
                        "last_error": str(exc)[:1000],
                        "next_retry_at": now + _RETRY_DELAY,
                        "completed_at": None,
                    }
                )
            )

    def _folder_for_operation(self, operation: str) -> str:
        if operation == BILL_DOCUMENT_OPERATION_MOVE_TO_PAID:
            return paid_invoices_folder(self._nas_base_path)
        if operation == BILL_DOCUMENT_OPERATION_GENERATE_PENDING:
            return pending_invoices_folder(self._nas_base_path)
        raise ValueError(f"Operación documental no soportada: {operation}")

    def _cleanup_previous_path(self, document: BillDocument, now: datetime) -> BillDocument:
        if not document.previous_nas_path or document.previous_nas_path == document.nas_path:
            return document

        try:
            self._file_storage.delete(document.previous_nas_path)
        except Exception as exc:
            logger.exception("No se pudo limpiar la ruta anterior del documento %s", document.id)
            return self._document_repository.update(
                document.model_copy(
                    update={
                        "status": BILL_DOCUMENT_STATUS_ERROR,
                        "last_error": str(exc)[:1000],
                        "next_retry_at": now + _RETRY_DELAY,
                        "completed_at": None,
                    }
                )
            )
        return self._document_repository.update(
            document.model_copy(update={"previous_nas_path": None})
        )
