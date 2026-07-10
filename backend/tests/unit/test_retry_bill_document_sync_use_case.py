"""
Unit tests — RetryBillDocumentSyncUseCase.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from application.bills.retry_bill_document_sync_use_case import RetryBillDocumentSyncUseCase
from domain.bills.bill_document import (
    BILL_DOCUMENT_OPERATION_GENERATE_PENDING,
    BILL_DOCUMENT_OPERATION_MOVE_TO_PAID,
    BILL_DOCUMENT_STATUS_COMPLETED,
    BILL_DOCUMENT_STATUS_ERROR,
)
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.repository import IBillRepository
from domain.exceptions import FileStorageError
from tests.helpers import make_bill, make_bill_document

pytestmark = pytest.mark.unit

_NAS_BASE = "/facturas"
_PDF_BYTES = b"%PDF-1.4 stub"


def _use_case(
    bills: MagicMock | None = None,
    documents: MagicMock | None = None,
    renderer: MagicMock | None = None,
    storage: MagicMock | None = None,
) -> RetryBillDocumentSyncUseCase:
    if bills is None:
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(bill_id=1)
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
    if renderer is None:
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES
    if storage is None:
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/1FACTURAS PENDIENTE/bill_1.pdf"

    return RetryBillDocumentSyncUseCase(bills, documents, renderer, storage, _NAS_BASE)


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

        result = _use_case(documents=documents).execute(limit=10)

        assert len(result) == 1
        assert result[0].status == BILL_DOCUMENT_STATUS_COMPLETED
        assert result[0].attempts == 2
        assert result[0].last_error is None
        documents.list_retryable.assert_called_once()
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

        result = _use_case(documents=documents, storage=storage).execute(limit=10)

        assert result[0].status == BILL_DOCUMENT_STATUS_COMPLETED
        storage.delete.assert_called_once_with("/facturas/1FACTURAS PENDIENTE/bill_1.pdf")
        assert documents.update.call_count == 2

    def test_failed_retry_keeps_error_and_schedules_next_attempt(self):
        storage = MagicMock()
        storage.upload_bytes.side_effect = FileStorageError("NAS caído")

        result = _use_case(storage=storage).execute(limit=10)

        assert result[0].status == BILL_DOCUMENT_STATUS_ERROR
        assert result[0].attempts == 2
        assert result[0].last_error is not None
        assert result[0].next_retry_at is not None
