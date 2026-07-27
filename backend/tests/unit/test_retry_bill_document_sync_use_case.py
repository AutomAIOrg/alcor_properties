"""
Unit tests — RetryBillDocumentSyncUseCase.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.bills.retry_bill_document_sync_use_case import RetryBillDocumentSyncUseCase
from domain.apartments.repository import IApartmentRepository
from domain.bills.bill_document import (
    BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
    BILL_DOCUMENT_OPERATION_MOVE_TO_PAID,
    BILL_DOCUMENT_STATUS_COMPLETED,
    BILL_DOCUMENT_STATUS_ERROR,
    BILL_DOCUMENT_STATUS_PENDING,
)
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.entity import BILL_STATE_PAID
from domain.bills.repository import IBillRepository
from domain.exceptions import FileStorageError
from tests.helpers import make_apartment, make_bill, make_bill_document

pytestmark = pytest.mark.unit

_NAS_BASE = "/facturas"
_PDF_BYTES = b"%PDF-1.4 stub"


def _use_case(
    bills: MagicMock | None = None,
    documents: MagicMock | None = None,
    renderer: MagicMock | None = None,
    storage: MagicMock | None = None,
    apartments: MagicMock | None = None,
) -> RetryBillDocumentSyncUseCase:
    if bills is None:
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(bill_id=1)
        bills.list_without_documents.return_value = []
    if documents is None:
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_retryable.return_value = [
            make_bill_document(
                id=10,
                status=BILL_DOCUMENT_STATUS_ERROR,
                operation=BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
                attempts=1,
                next_retry_at=datetime(2026, 6, 1, 13, 0, tzinfo=UTC),
            )
        ]
        documents.update.side_effect = lambda doc: doc
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 99})
    if renderer is None:
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES
    if storage is None:
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/1FACTURAS PENDIENTE/bill_1.pdf"
    if apartments is None:
        apartments = MagicMock(spec=IApartmentRepository)
        apartments.get_by_apartment_id.return_value = make_apartment()

    return RetryBillDocumentSyncUseCase(bills, documents, apartments, renderer, storage, _NAS_BASE)


class TestRetryBillDocumentSyncUseCase:
    def test_retries_pending_generation_and_marks_completed(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_retryable.return_value = [
            make_bill_document(
                id=10,
                status=BILL_DOCUMENT_STATUS_ERROR,
                operation=BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
                attempts=1,
            )
        ]
        documents.update.side_effect = lambda doc: doc

        result = _use_case(documents=documents).execute(limit=10, uploaded_by=2)

        assert len(result) == 1
        assert result[0].status == BILL_DOCUMENT_STATUS_COMPLETED
        assert result[0].attempts == 2
        assert result[0].last_error is None
        documents.list_retryable.assert_called_once()
        assert documents.list_retryable.call_args.kwargs["stale_processing_before"] is not None
        documents.update.assert_called_once()

    def test_retries_move_and_clears_previous_path_after_cleanup(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_retryable.return_value = [
            make_bill_document(
                id=10,
                status=BILL_DOCUMENT_STATUS_ERROR,
                operation=BILL_DOCUMENT_OPERATION_MOVE_TO_PAID,
                attempts=1,
                previous_nas_path="/facturas/1FACTURAS PENDIENTE/bill_1.pdf",
            )
        ]
        documents.update.side_effect = lambda doc: doc
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/1FACTURAS PAGADAS/bill_1.pdf"

        result = _use_case(documents=documents, storage=storage).execute(limit=10, uploaded_by=2)

        assert result[0].status == BILL_DOCUMENT_STATUS_COMPLETED
        storage.delete.assert_called_once_with("/facturas/1FACTURAS PENDIENTE/bill_1.pdf")
        assert documents.update.call_count == 2

    def test_failed_retry_keeps_error_and_schedules_next_attempt(self):
        storage = MagicMock()
        storage.upload_bytes.side_effect = FileStorageError("NAS caído")

        result = _use_case(storage=storage).execute(limit=10, uploaded_by=2)

        assert result[0].status == BILL_DOCUMENT_STATUS_ERROR
        assert result[0].attempts == 2
        assert result[0].last_error is not None
        assert result[0].next_retry_at is not None

    def test_creates_and_syncs_orphan_bills_without_documents(self):
        orphan = make_bill(bill_id=8, apartment_id="PM69")
        bills = MagicMock(spec=IBillRepository)
        bills.list_without_documents.return_value = [orphan]
        bills.get_by_id.return_value = orphan
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_retryable.return_value = []
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 50})
        documents.update.side_effect = lambda doc: doc
        storage = MagicMock()
        storage.upload_bytes.return_value = (
            "/facturas/1FACTURAS PENDIENTE/PM69 LIMPIEZA 01.06.2026.pdf"
        )

        result = _use_case(bills=bills, documents=documents, storage=storage).execute(
            limit=10, uploaded_by=2
        )

        assert len(result) == 1
        assert result[0].status == BILL_DOCUMENT_STATUS_COMPLETED
        documents.create.assert_called_once()
        created = documents.create.call_args.args[0]
        assert created.status == BILL_DOCUMENT_STATUS_PENDING
        assert created.operation == BILL_DOCUMENT_OPERATION_GENERATE_PENDING
        assert created.uploaded_by == 2
        documents.list_retryable.assert_called_once()
        assert documents.list_retryable.call_args.kwargs["limit"] == 9

    def test_orphan_paid_bill_uses_move_to_paid_operation(self):
        orphan = make_bill(bill_id=9, state=BILL_STATE_PAID)
        bills = MagicMock(spec=IBillRepository)
        bills.list_without_documents.return_value = [orphan]
        bills.get_by_id.return_value = orphan
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.list_retryable.return_value = []
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 51})
        documents.update.side_effect = lambda doc: doc
        storage = MagicMock()
        storage.upload_bytes.return_value = (
            "/facturas/1FACTURAS PAGADAS/TEST-001 LIMPIEZA 01.06.2026.pdf"
        )

        result = _use_case(bills=bills, documents=documents, storage=storage).execute(
            limit=10, uploaded_by=3
        )

        assert result[0].status == BILL_DOCUMENT_STATUS_COMPLETED
        created = documents.create.call_args.args[0]
        assert created.operation == BILL_DOCUMENT_OPERATION_MOVE_TO_PAID
        call_kwargs = storage.upload_bytes.call_args.kwargs
        assert call_kwargs["remote_folder"] == "/facturas/1FACTURAS PAGADAS"
