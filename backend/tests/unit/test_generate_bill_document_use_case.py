"""
Unit tests — GenerateAndStoreBillDocumentUseCase.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from application.bills.generate_and_store_bill_document_use_case import (
    GenerateAndStoreBillDocumentUseCase,
)
from domain.apartments.repository import IApartmentRepository
from domain.bills.bill_document import (
    BILL_DOCUMENT_STATUS_COMPLETED,
    BILL_DOCUMENT_STATUS_ERROR,
    BILL_DOCUMENT_STATUS_PROCESSING,
)
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.bills.repository import IBillRepository
from domain.exceptions import (
    BillNotFoundError,
    DomainValidationError,
    FileStorageError,
)
from tests.helpers import make_apartment, make_bill, make_bill_document

pytestmark = pytest.mark.unit

_NAS_BASE = "/facturas"
_PDF_BYTES = b"%PDF-1.4 stub"
_PENDING_FOLDER = "/facturas/1FACTURAS PENDIENTE"


def _use_case(
    bills: MagicMock | None = None,
    documents: MagicMock | None = None,
    apartments: MagicMock | None = None,
    renderer: MagicMock | None = None,
    storage: MagicMock | None = None,
) -> GenerateAndStoreBillDocumentUseCase:
    if bills is None:
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(bill_id=1)
    if documents is None:
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = None
        documents.list_by_bill_id.return_value = []
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 10})
        documents.update.side_effect = lambda doc: doc
    if apartments is None:
        apartments = MagicMock(spec=IApartmentRepository)
        apartments.get_by_apartment_id.return_value = make_apartment(address="Calle Glaucio 15")
    if renderer is None:
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES
    if storage is None:
        storage = MagicMock()
        storage.upload_bytes.return_value = f"{_PENDING_FOLDER}/TEST-001 LIMPIEZA 01.06.2026.pdf"

    return GenerateAndStoreBillDocumentUseCase(
        bills, documents, apartments, renderer, storage, _NAS_BASE
    )


class TestGenerateAndStoreBillDocumentUseCase:
    def test_happy_path_claims_processing_before_upload(self):
        bill = make_bill(bill_id=1)
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = bill
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = None
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 10})
        documents.update.side_effect = lambda doc: doc
        renderer = MagicMock()
        renderer.render.return_value = _PDF_BYTES
        storage = MagicMock()
        storage.upload_bytes.return_value = f"{_PENDING_FOLDER}/TEST-001 LIMPIEZA 01.06.2026.pdf"

        call_order: list[str] = []

        def track_create(doc):
            call_order.append(f"create:{doc.status}")
            return doc.model_copy(update={"id": 10})

        def track_upload(**_kwargs):
            call_order.append("upload")
            return f"{_PENDING_FOLDER}/TEST-001 LIMPIEZA 01.06.2026.pdf"

        def track_update(doc):
            call_order.append(f"update:{doc.status}")
            return doc

        documents.create.side_effect = track_create
        documents.update.side_effect = track_update
        storage.upload_bytes.side_effect = track_upload

        result = _use_case(bills, documents, None, renderer, storage).execute(1, uploaded_by=2)

        assert result.id == 10
        assert result.bill_id == 1
        assert result.status == BILL_DOCUMENT_STATUS_COMPLETED
        assert result.nas_path.endswith(".pdf")
        assert call_order[0] == f"create:{BILL_DOCUMENT_STATUS_PROCESSING}"
        assert "upload" in call_order
        assert call_order.index(f"create:{BILL_DOCUMENT_STATUS_PROCESSING}") < call_order.index(
            "upload"
        )

        renderer.render.assert_called_once()
        pdf_data = renderer.render.call_args.args[0]
        assert pdf_data.bill_id == 1
        assert pdf_data.apartment_id == bill.apartment_id
        assert pdf_data.cleaning_date == bill.cleaning_date
        assert pdf_data.clean_hours == bill.clean_hours
        assert pdf_data.hourly_rate == bill.hourly_rate
        assert pdf_data.cost == bill.cost
        assert pdf_data.address == "Calle Glaucio 15"
        assert pdf_data.paid is False

        call_kwargs = storage.upload_bytes.call_args.kwargs
        assert call_kwargs["remote_folder"] == _PENDING_FOLDER
        assert call_kwargs["content"] == _PDF_BYTES
        documents.create.assert_called_once()
        documents.update.assert_called()

    def test_resolves_address_even_when_apartment_missing(self):
        apartments = MagicMock(spec=IApartmentRepository)
        apartments.get_by_apartment_id.return_value = None

        _use_case(apartments=apartments).execute(1, uploaded_by=2)

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

    def test_raises_when_cost_missing(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(cost=None)

        with pytest.raises(DomainValidationError, match="coste"):
            _use_case(bills=bills).execute(1, uploaded_by=2)

    def test_marks_document_as_error_when_nas_upload_fails(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = None
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 10})
        documents.update.side_effect = lambda doc: doc
        storage = MagicMock()
        storage.upload_bytes.side_effect = FileStorageError("NAS caído")

        result = _use_case(documents=documents, storage=storage).execute(1, uploaded_by=2)

        assert result.status == BILL_DOCUMENT_STATUS_ERROR
        assert result.last_error is not None
        assert result.next_retry_at is not None
        documents.create.assert_called_once()
        assert documents.create.call_args.args[0].status == BILL_DOCUMENT_STATUS_PROCESSING
        documents.update.assert_called_once()
        assert documents.update.call_args.args[0].status == BILL_DOCUMENT_STATUS_ERROR

    def test_raises_and_deletes_nas_file_when_final_persist_fails(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = None
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 10})
        documents.update.side_effect = RuntimeError("db down")
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/2026-06-01/bill_1.pdf"

        with pytest.raises(FileStorageError, match="base de datos"):
            _use_case(documents=documents, storage=storage).execute(1, uploaded_by=2)

        storage.delete.assert_called_once_with("/facturas/2026-06-01/bill_1.pdf")

    def test_raises_even_when_nas_delete_fails_after_db_persist_error(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = None
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 10})
        documents.update.side_effect = RuntimeError("db down")
        storage = MagicMock()
        storage.upload_bytes.return_value = "/facturas/2026-06-01/bill_1.pdf"
        storage.delete.side_effect = FileStorageError("delete failed")

        with pytest.raises(FileStorageError, match="base de datos"):
            _use_case(documents=documents, storage=storage).execute(1, uploaded_by=2)

        storage.delete.assert_called_once_with("/facturas/2026-06-01/bill_1.pdf")

    def test_returns_existing_document_when_document_already_exists(self):
        existing = make_bill_document()
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = existing

        result = _use_case(documents=documents).execute(1, uploaded_by=2)

        assert result == existing
        documents.create.assert_not_called()

    def test_returns_error_document_when_nas_fails_after_claim(self):
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = None
        documents.create.side_effect = lambda doc: doc.model_copy(update={"id": 10})
        documents.update.side_effect = lambda doc: doc
        storage = MagicMock()
        storage.upload_bytes.side_effect = FileStorageError("NAS caído")

        result = _use_case(documents=documents, storage=storage).execute(1, uploaded_by=2)

        assert result.status == BILL_DOCUMENT_STATUS_ERROR
        storage.delete.assert_not_called()

    def test_regenerate_updates_existing_document_in_place(self):
        existing = make_bill_document(
            id=10, nas_path=f"{_PENDING_FOLDER}/TEST-001 LIMPIEZA 01.06.2026.pdf"
        )
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = existing
        documents.update.side_effect = lambda doc: doc
        storage = MagicMock()
        storage.upload_bytes.return_value = existing.nas_path

        result = _use_case(documents=documents, storage=storage).execute(
            1, uploaded_by=2, regenerate=True
        )

        assert result.id == 10
        assert result.status == BILL_DOCUMENT_STATUS_COMPLETED
        assert documents.update.call_count == 2
        assert documents.update.call_args_list[0].args[0].status == BILL_DOCUMENT_STATUS_PROCESSING
        assert documents.update.call_args_list[1].args[0].status == BILL_DOCUMENT_STATUS_COMPLETED
        documents.create.assert_not_called()
        storage.delete.assert_not_called()

    def test_regenerate_cleans_up_previous_file_when_filename_changes(self):
        bills = MagicMock(spec=IBillRepository)
        bills.get_by_id.return_value = make_bill(bill_id=1, cleaning_date=date(2026, 6, 3))
        old_path = f"{_PENDING_FOLDER}/TEST-001 LIMPIEZA 01.06.2026.pdf"
        new_path = f"{_PENDING_FOLDER}/TEST-001 LIMPIEZA 03.06.2026.pdf"
        existing = make_bill_document(id=10, nas_path=old_path)
        documents = MagicMock(spec=IBillDocumentRepository)
        documents.get_by_bill_id.return_value = existing
        documents.update.side_effect = lambda doc: doc
        storage = MagicMock()
        storage.upload_bytes.return_value = new_path

        result = _use_case(bills=bills, documents=documents, storage=storage).execute(
            1, uploaded_by=2, regenerate=True
        )

        assert result.id == 10
        assert result.nas_path == new_path
        storage.delete.assert_called_once_with(old_path)
