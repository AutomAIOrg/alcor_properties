"""
Caso de uso: generar documento PDF de factura y almacenarlo en NAS.
"""

import logging
from datetime import UTC, datetime, timedelta

from application.bills.bill_document_helpers import (
    CONTENT_TYPE_PDF,
    build_bill_document_filename,
    build_bill_pdf_data,
    pending_invoices_folder,
    validate_bill_for_document,
)
from application.bills.bill_pdf_renderer_interface import IBillPdfRenderer
from application.shared.file_storage_interface import IFileStorage
from domain.apartments.repository import IApartmentRepository
from domain.bills.bill_document import (
    BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
    BILL_DOCUMENT_STATUS_COMPLETED,
    BILL_DOCUMENT_STATUS_ERROR,
    BillDocument,
)
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.repository import IBillRepository
from domain.exceptions import FileStorageError

logger = logging.getLogger(__name__)


class GenerateAndStoreBillDocumentUseCase:
    """
    Orquesta la generación del PDF de factura (vía renderer) y su subida al NAS.

    Los datos del documento se derivan de la factura persistida; la dirección del
    apartamento se resuelve desde el repositorio de apartamentos. La generación real del
    PDF se delega en IBillPdfRenderer (Chromium headless).
    """

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

    def execute(self, bill_id: int, uploaded_by: int, *, regenerate: bool = False) -> BillDocument:
        """
        Genera y sube el recibo pendiente de la factura.

        Por defecto es idempotente: si ya existe un documento para la factura lo devuelve
        sin volver a generarlo (evita subidas duplicadas al recrear). Con ``regenerate=True``
        (rectificación) vuelve a renderizar el PDF con los datos actuales y actualiza el
        documento existente EN EL SITIO —nunca crea un segundo documento—, sustituyendo el
        archivo del NAS y limpiando el anterior si su nombre cambió (p. ej. otra fecha).
        """
        bill = self._bill_repository.get_by_id(bill_id)
        validate_bill_for_document(bill)

        existing_document = self._document_repository.get_by_bill_id(bill_id)
        if existing_document is not None and not regenerate:
            return existing_document

        assert bill.cleaning_date is not None
        remote_folder = pending_invoices_folder(self._nas_base_path)
        filename = build_bill_document_filename(bill.apartment_id, bill.cleaning_date)
        now = datetime.now(UTC)
        old_nas_path = existing_document.nas_path if existing_document else None

        try:
            pdf_data = build_bill_pdf_data(bill, bill_id, self._apartment_repository)
            content = self._pdf_renderer.render(pdf_data)
            nas_path = self._file_storage.upload_bytes(
                remote_folder=remote_folder,
                filename=filename,
                content=content,
                content_type=CONTENT_TYPE_PDF,
            )
            document = BillDocument(
                id=existing_document.id if existing_document else None,
                bill_id=bill_id,
                filename=filename,
                nas_path=nas_path,
                content_type=CONTENT_TYPE_PDF,
                size_bytes=len(content),
                uploaded_by=uploaded_by,
                uploaded_at=now,
                status=BILL_DOCUMENT_STATUS_COMPLETED,
                operation=BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
                attempts=(existing_document.attempts if existing_document else 0) + 1,
                completed_at=now,
                previous_nas_path=(
                    old_nas_path if old_nas_path and old_nas_path != nas_path else None
                ),
            )
        except FileStorageError:
            document = self._failed_document(
                existing_document=existing_document,
                bill_id=bill_id,
                filename=filename,
                nas_path=f"{remote_folder}/{filename}",
                uploaded_by=uploaded_by,
                uploaded_at=now,
                old_nas_path=old_nas_path,
                error="No se pudo almacenar el documento de factura en el NAS.",
            )
        except Exception as exc:
            logger.exception("Error inesperado al subir documento de factura %s al NAS", bill_id)
            document = self._failed_document(
                existing_document=existing_document,
                bill_id=bill_id,
                filename=filename,
                nas_path=f"{remote_folder}/{filename}",
                uploaded_by=uploaded_by,
                uploaded_at=now,
                old_nas_path=old_nas_path,
                error=str(exc),
            )

        try:
            if existing_document is not None:
                persisted = self._document_repository.update(document)
            else:
                persisted = self._document_repository.create(document)
        except Exception as exc:
            if document.status == BILL_DOCUMENT_STATUS_COMPLETED:
                self._compensate_upload(document.nas_path)
            logger.error(
                "Falló la persistencia del estado documental (%s) para factura %s",
                document.nas_path,
                bill_id,
            )
            raise FileStorageError(
                "No se pudo registrar el estado del documento de factura en la base de datos."
            ) from exc

        # Al regenerar con cambio de nombre (p. ej. otra fecha de limpieza), el archivo anterior
        # del NAS queda huérfano: se elimina para no dejar dos PDF de la misma factura.
        if (
            document.status == BILL_DOCUMENT_STATUS_COMPLETED
            and old_nas_path
            and old_nas_path != persisted.nas_path
        ):
            try:
                self._file_storage.delete(old_nas_path)
            except Exception:
                logger.exception(
                    "No se pudo eliminar el documento anterior %s tras regenerar factura %s",
                    old_nas_path,
                    bill_id,
                )

        return persisted

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
            # Si ya existía, se conserva la ruta válida previa (el PDF anterior sigue en el NAS).
            nas_path=existing_document.nas_path if existing_document else nas_path,
            filename=filename,
            content_type=CONTENT_TYPE_PDF,
            size_bytes=existing_document.size_bytes if existing_document else 0,
            uploaded_by=uploaded_by,
            uploaded_at=uploaded_at,
            status=BILL_DOCUMENT_STATUS_ERROR,
            operation=BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
            attempts=(existing_document.attempts if existing_document else 0) + 1,
            last_error=error[:1000],
            next_retry_at=uploaded_at + timedelta(hours=1),
            previous_nas_path=old_nas_path if existing_document else None,
        )

    def _compensate_upload(self, nas_path: str) -> None:
        try:
            self._file_storage.delete(nas_path)
        except Exception:
            logger.exception("No se pudo eliminar el archivo huérfano en NAS: %s", nas_path)
