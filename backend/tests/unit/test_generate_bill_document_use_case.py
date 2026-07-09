"""
Unit tests — GenerateAndStoreBillDocumentUseCase.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from application.bills.bill_pdf_renderer_interface import BillPdfData
from application.bills.generate_and_store_bill_document_use_case import (
    GenerateAndStoreBillDocumentUseCase,
)
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.repository import IBillRepository
from domain.exceptions import (
    BillDocumentAlreadyExistsError,
    BillNotFoundError,
    DomainValidationError,
    FileStorageError,
)
from tests.helpers import make_bill, make_bill_document

pytestmark = pytest.mark.unit

_NAS_BASE = "/facturas"
_PDF_BYTES = b"%PDF-1.4 stub"


def _use_case(
    bills: MagicMock | None = None,
    documents: MagicMock | None = None,
    renderer: MagicMock | None = None,
    storage: MagicMock | None = None,
) -> GenerateAndStoreBillDocumentUseCase:
    if bills is None:
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(bill_id=1)
    if documents is None:
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = []
        documents.create.side_effect = lambda doc: doc
    if renderer is None:
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES
    if storage is None:
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/2026-06-01/bill_1_20260601_abcd1234.pdf"

    return GenerateAndStoreBillDocumentUseCase(bills, documents, renderer, storage, _NAS_BASE)


class TestGenerateAndStoreBillDocumentUseCase:
    def test_happy_path_renders_uploads_and_persists(self):
        bill = make_bill(bill_id=1)
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = bill
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = []
        documents.create.side_effect = lambda doc: make_bill_document(
            id=10,
            bill_id=doc.bill_id,
            filename=doc.filename,
            nas_path=doc.nas_path,
            size_bytes=doc.size_bytes,
            uploaded_by=doc.uploaded_by,
            uploaded_at=doc.uploaded_at,
        )
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/2026-06-01/bill_1_20260601_abcd1234.pdf"

        result = _use_case(bills, documents, renderer, storage).execute(1, uploaded_by=2)

        assert result.id == 10
        assert result.bill_id == 1
        assert result.nas_path.endswith(".pdf")
        renderer.render.assert_called_once_with(
            BillPdfData(
                bill_id=1,
                cleaning_date=bill.cleaning_date,
                apartment_id=bill.apartment_id,
                clean_hours=bill.clean_hours,
                hourly_rate=bill.hourly_rate,
            )
        )
        storage.upload_bytes.assert_called_once()
        call_kwargs = storage.upload_bytes.call_args.kwargs
        assert call_kwargs["remote_folder"] == "/facturas/TEST-001 LIMPIEZAS/2026"
        assert call_kwargs["content"] == _PDF_BYTES
        documents.create.assert_called_once()

    def test_raises_when_bill_not_found(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.side_effect = BillNotFoundError(99)

        with pytest.raises(BillNotFoundError):
            _use_case(bills=bills).execute(99, uploaded_by=2)

    def test_raises_when_cleaning_date_missing(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(cleaning_date=None)

        with pytest.raises(DomainValidationError, match="fecha de limpieza"):
            _use_case(bills=bills).execute(1, uploaded_by=2)

    def test_raises_when_clean_hours_invalid(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(clean_hours=Decimal("0"))

        with pytest.raises(DomainValidationError, match="horas"):
            _use_case(bills=bills).execute(1, uploaded_by=2)

    def test_raises_when_hourly_rate_missing(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(hourly_rate=None)

        with pytest.raises(DomainValidationError, match="tarifa"):
            _use_case(bills=bills).execute(1, uploaded_by=2)

    def test_raises_when_nas_upload_fails(self):
        storage = MagicMock()
        storage.upload_bytes.side_effect = FileStorageError("NAS caído")

        with pytest.raises(FileStorageError, match="NAS"):
            _use_case(storage=storage).execute(1, uploaded_by=2)

    def test_raises_and_deletes_nas_file_when_db_persist_fails(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = []
        documents.create.side_effect = RuntimeError("db down")
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/2026-06-01/bill_1.pdf"

        with pytest.raises(FileStorageError, match="base de datos"):
            _use_case(documents=documents, storage=storage).execute(1, uploaded_by=2)

        storage.delete.assert_called_once_with("/facturas/2026-06-01/bill_1.pdf")

    def test_raises_even_when_nas_delete_fails_after_db_persist_error(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = []
        documents.create.side_effect = RuntimeError("db down")
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/2026-06-01/bill_1.pdf"
        storage.delete.side_effect = FileStorageError("delete failed")

        with pytest.raises(FileStorageError, match="base de datos"):
            _use_case(documents=documents, storage=storage).execute(1, uploaded_by=2)

        storage.delete.assert_called_once_with("/facturas/2026-06-01/bill_1.pdf")

    def test_raises_when_document_already_exists(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = [make_bill_document()]

        with pytest.raises(BillDocumentAlreadyExistsError, match="1"):
            _use_case(documents=documents).execute(1, uploaded_by=2)

    def test_deletes_nas_file_when_document_already_exists_on_persist(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = []
        documents.create.side_effect = BillDocumentAlreadyExistsError(1)
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/2026-06-01/bill_1.pdf"

        with pytest.raises(BillDocumentAlreadyExistsError):
            _use_case(documents=documents, storage=storage).execute(1, uploaded_by=2)

        storage.delete.assert_called_once_with("/facturas/2026-06-01/bill_1.pdf")
