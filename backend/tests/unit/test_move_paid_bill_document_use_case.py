"""
Unit tests — MovePaidBillDocumentUseCase.
"""

from unittest.mock import MagicMock

import pytest

from application.bills.move_paid_bill_document_use_case import MovePaidBillDocumentUseCase
from domain.apartments.repository import IApartmentRepository
from domain.bills.bill_document import BILL_DOCUMENT_STATUS_COMPLETED, BILL_DOCUMENT_STATUS_ERROR
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.repository import IBillRepository
from domain.exceptions import BillNotFoundError, DomainValidationError, FileStorageError
from tests.helpers import make_apartment, make_bill, make_bill_document

pytestmark = pytest.mark.unit

_NAS_BASE = "/facturas"
_PDF_BYTES = b"%PDF-1.4 stub"
_PENDING_PATH = "/facturas/1FACTURAS PENDIENTE/TEST-001 LIMPIEZA 01.06.2026.pdf"
_PAID_PATH = "/facturas/1FACTURAS PAGADAS/TEST-001 LIMPIEZA 01.06.2026.pdf"


def _use_case(
    bills: MagicMock | None = None,
    documents: MagicMock | None = None,
    renderer: MagicMock | None = None,
    storage: MagicMock | None = None,
    apartments: MagicMock | None = None,
) -> MovePaidBillDocumentUseCase:
    if bills is None:
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(bill_id=1)
    if documents is None:
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = [make_bill_document(id=10, nas_path=_PENDING_PATH)]
        documents.update.side_effect = lambda doc: doc
    if apartments is None:
        apartments = MagicMock(spec=IApartmentRepository)
        apartments.get_by_apartment_id.return_value = make_apartment()
    if renderer is None:
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES
    if storage is None:
        storage = MagicMock()
        storage.upload_bytes.return_value = _PAID_PATH

    return MovePaidBillDocumentUseCase(
        bills, documents, apartments, renderer, storage, _NAS_BASE
    )


class TestMovePaidBillDocumentUseCase:
    def test_moves_existing_document_to_paid_folder(self):
        bill = make_bill(bill_id=1)
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = bill
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = [make_bill_document(id=10, nas_path=_PENDING_PATH)]
        documents.update.side_effect = lambda doc: doc
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES
        storage = MagicMock()
        storage.upload_bytes.return_value = _PAID_PATH

        result = _use_case(bills, documents, renderer, storage).execute(1, uploaded_by=2)

        assert result.nas_path == _PAID_PATH
        assert result.status == BILL_DOCUMENT_STATUS_COMPLETED
        renderer.render.assert_called_once()
        pdf_data = renderer.render.call_args.args[0]
        assert pdf_data.bill_id == 1
        assert pdf_data.cleaning_date == bill.cleaning_date
        assert pdf_data.apartment_id == bill.apartment_id
        assert pdf_data.clean_hours == bill.clean_hours
        assert pdf_data.hourly_rate == bill.hourly_rate
        assert pdf_data.cost == bill.cost
        call_kwargs = storage.upload_bytes.call_args.kwargs
        assert call_kwargs["remote_folder"] == "/facturas/1FACTURAS PAGADAS"
        documents.update.assert_called_once()
        documents.create.assert_not_called()
        storage.delete.assert_called_once_with(_PENDING_PATH)

    def test_creates_document_in_paid_folder_when_missing(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = []
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 11})

        result = _use_case(documents=documents).execute(1, uploaded_by=2)

        assert result.id == 11
        assert result.nas_path == _PAID_PATH
        documents.create.assert_called_once()
        documents.update.assert_not_called()

    def test_raises_when_bill_not_found(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.side_effect = BillNotFoundError(99)

        with pytest.raises(BillNotFoundError):
            _use_case(bills=bills).execute(99, uploaded_by=2)

    def test_raises_when_hourly_rate_missing(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(hourly_rate=None)

        with pytest.raises(DomainValidationError, match="tarifa"):
            _use_case(bills=bills).execute(1, uploaded_by=2)

    def test_marks_document_as_error_when_nas_upload_fails(self):
        storage = MagicMock()
        storage.upload_bytes.side_effect = FileStorageError("NAS caído")

        result = _use_case(storage=storage).execute(1, uploaded_by=2)

        assert result.status == BILL_DOCUMENT_STATUS_ERROR
        assert result.last_error is not None
        assert result.next_retry_at is not None

    def test_compensates_upload_when_db_update_fails(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_by_bill_id.return_value = [make_bill_document(id=10, nas_path=_PENDING_PATH)]
        documents.update.side_effect = RuntimeError("db down")
        storage = MagicMock()
        storage.upload_bytes.return_value = _PAID_PATH

        with pytest.raises(FileStorageError, match="base de datos"):
            _use_case(documents=documents, storage=storage).execute(1, uploaded_by=2)

        storage.delete.assert_called_once_with(_PAID_PATH)

    def test_marks_document_as_error_when_pending_delete_fails(self):
        storage = MagicMock()
        storage.upload_bytes.return_value = _PAID_PATH
        storage.delete.side_effect = FileStorageError("delete failed")

        result = _use_case(storage=storage).execute(1, uploaded_by=2)

        assert result.status == BILL_DOCUMENT_STATUS_ERROR
        assert result.previous_nas_path == _PENDING_PATH
