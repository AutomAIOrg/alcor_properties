"""
Integration tests — SQLAlchemyBillDocumentRepository.
"""

from datetime import UTC, datetime

import pytest
from passlib.context import CryptContext

from domain.bills.bill_document import BILL_DOCUMENT_STATUS_ERROR, BillDocument
from domain.exceptions import BillDocumentAlreadyExistsError
from infrastructure.models.bill import BillORM
from infrastructure.models.user import UserORM
from infrastructure.repositories.sqlalchemy_bill_document_repository import (
    SQLAlchemyBillDocumentRepository,
)

pytestmark = pytest.mark.integration


def _seed_bill_and_user(sqlite_session):
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    user = UserORM(
        username="limpiadora",
        password=pwd.hash("pass"),
        name="Limpiadora",
        lastname="Test",
        email="limpiadora@example.com",
        role="limpiadora",
    )
    sqlite_session.add(user)
    sqlite_session.flush()

    bill = BillORM(
        record_id=None,
        cleaning_date=datetime(2026, 6, 1).date(),
        clean_hours=2,
        cost=30,
        apartment_id="TEST-001",
        state="Creada",
    )
    sqlite_session.add(bill)
    sqlite_session.commit()
    return bill.bill_id, user.id


class TestSQLAlchemyBillDocumentRepository:
    def test_create_and_list_by_bill_id(self, sqlite_session):
        bill_id, user_id = _seed_bill_and_user(sqlite_session)
        repo = SQLAlchemyBillDocumentRepository(sqlite_session)

        document = BillDocument(
            bill_id=bill_id,
            filename="bill_1.pdf",
            nas_path="/facturas/2026-06-01/bill_1.pdf",
            content_type="application/pdf",
            size_bytes=128,
            uploaded_by=user_id,
            uploaded_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        )
        created = repo.create(document)

        assert created.id is not None
        assert created.bill_id == bill_id

        listed = repo.list_by_bill_id(bill_id)
        assert len(listed) == 1
        assert listed[0].filename == "bill_1.pdf"

    def test_create_duplicate_bill_id_raises(self, sqlite_session):
        bill_id, user_id = _seed_bill_and_user(sqlite_session)
        repo = SQLAlchemyBillDocumentRepository(sqlite_session)

        document = BillDocument(
            bill_id=bill_id,
            filename="bill_1.pdf",
            nas_path="/facturas/2026-06-01/bill_1.pdf",
            content_type="application/pdf",
            size_bytes=128,
            uploaded_by=user_id,
            uploaded_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
        )
        repo.create(document)

        duplicate = BillDocument(
            bill_id=bill_id,
            filename="bill_1_copy.pdf",
            nas_path="/facturas/2026-06-01/bill_1_copy.pdf",
            content_type="application/pdf",
            size_bytes=256,
            uploaded_by=user_id,
            uploaded_at=datetime(2026, 6, 1, 11, 0, tzinfo=UTC),
        )

        with pytest.raises(BillDocumentAlreadyExistsError, match=str(bill_id)):
            repo.create(duplicate)

    def test_update_changes_nas_path(self, sqlite_session):
        bill_id, user_id = _seed_bill_and_user(sqlite_session)
        repo = SQLAlchemyBillDocumentRepository(sqlite_session)

        created = repo.create(
            BillDocument(
                bill_id=bill_id,
                filename="bill_1.pdf",
                nas_path="/facturas/1FACTURAS PENDIENTE/bill_1.pdf",
                content_type="application/pdf",
                size_bytes=128,
                uploaded_by=user_id,
                uploaded_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
            )
        )

        updated = repo.update(
            created.model_copy(
                update={
                    "filename": "bill_1_paid.pdf",
                    "nas_path": "/facturas/1FACTURAS PAGADAS/bill_1_paid.pdf",
                    "size_bytes": 256,
                    "uploaded_at": datetime(2026, 6, 2, 10, 0, tzinfo=UTC),
                }
            )
        )

        assert updated.filename == "bill_1_paid.pdf"
        assert updated.nas_path == "/facturas/1FACTURAS PAGADAS/bill_1_paid.pdf"
        assert updated.size_bytes == 256
        listed = repo.list_by_bill_id(bill_id)
        assert len(listed) == 1
        assert listed[0].nas_path == "/facturas/1FACTURAS PAGADAS/bill_1_paid.pdf"

    def test_list_retryable_returns_due_error_documents(self, sqlite_session):
        bill_id, user_id = _seed_bill_and_user(sqlite_session)
        repo = SQLAlchemyBillDocumentRepository(sqlite_session)

        retry_at = datetime(2026, 6, 1, 11, 0, tzinfo=UTC)
        repo.create(
            BillDocument(
                bill_id=bill_id,
                filename="bill_1.pdf",
                nas_path="/facturas/1FACTURAS PENDIENTE/bill_1.pdf",
                content_type="application/pdf",
                size_bytes=0,
                uploaded_by=user_id,
                uploaded_at=datetime(2026, 6, 1, 10, 0, tzinfo=UTC),
                status=BILL_DOCUMENT_STATUS_ERROR,
                attempts=1,
                last_error="NAS caído",
                next_retry_at=retry_at,
            )
        )

        retryable = repo.list_retryable(datetime(2026, 6, 1, 12, 0, tzinfo=UTC))

        assert len(retryable) == 1
        assert retryable[0].status == BILL_DOCUMENT_STATUS_ERROR
        assert retryable[0].next_retry_at == retry_at.replace(tzinfo=None)
