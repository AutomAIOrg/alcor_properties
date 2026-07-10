"""
Implementación de IBillDocumentRepository usando SQLAlchemy.
"""

from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.bills.bill_document import (
    BILL_DOCUMENT_STATUS_ERROR,
    BILL_DOCUMENT_STATUS_PENDING,
    BillDocument,
)
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.exceptions import (
    BillDocumentAlreadyExistsError,
    BillDocumentNotFoundError,
    BillDocumentNotUpdatedError,
)
from infrastructure.models.bill_document import BillDocumentORM


class SQLAlchemyBillDocumentRepository(IBillDocumentRepository):
    """Repositorio de documentos de factura respaldado por SQLAlchemy."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, document: BillDocument) -> BillDocument:
        orm = BillDocumentORM(
            bill_id=document.bill_id,
            filename=document.filename,
            nas_path=document.nas_path,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            uploaded_by=document.uploaded_by,
            uploaded_at=document.uploaded_at,
            status=document.status,
            operation=document.operation,
            attempts=document.attempts,
            last_error=document.last_error,
            next_retry_at=document.next_retry_at,
            completed_at=document.completed_at,
            previous_nas_path=document.previous_nas_path,
        )
        self._db.add(orm)
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            if document.bill_id is not None and self.list_by_bill_id(document.bill_id):
                raise BillDocumentAlreadyExistsError(document.bill_id) from exc
            raise
        self._db.refresh(orm)
        return self._to_entity(orm)

    def list_by_bill_id(self, bill_id: int) -> list[BillDocument]:
        rows = (
            self._db.query(BillDocumentORM)
            .filter(BillDocumentORM.bill_id == bill_id)
            .order_by(BillDocumentORM.uploaded_at.desc())
            .all()
        )
        return [self._to_entity(orm) for orm in rows]

    def get_by_bill_id(self, bill_id: int) -> BillDocument | None:
        orm = (
            self._db.query(BillDocumentORM)
            .filter(BillDocumentORM.bill_id == bill_id)
            .order_by(BillDocumentORM.uploaded_at.desc())
            .first()
        )
        return self._to_entity(orm) if orm is not None else None

    def update(self, document: BillDocument) -> BillDocument:
        if document.id is None:
            raise BillDocumentNotFoundError(document.bill_id)

        orm = (
            self._db.query(BillDocumentORM).filter(BillDocumentORM.id == document.id).one_or_none()
        )
        if orm is None:
            raise BillDocumentNotFoundError(document.bill_id)

        orm.filename = document.filename
        orm.nas_path = document.nas_path
        orm.content_type = document.content_type
        orm.size_bytes = document.size_bytes
        orm.uploaded_by = document.uploaded_by
        orm.uploaded_at = document.uploaded_at
        orm.status = document.status
        orm.operation = document.operation
        orm.attempts = document.attempts
        orm.last_error = document.last_error
        orm.next_retry_at = document.next_retry_at
        orm.completed_at = document.completed_at
        orm.previous_nas_path = document.previous_nas_path
        try:
            self._db.commit()
        except IntegrityError as exc:
            self._db.rollback()
            raise BillDocumentNotUpdatedError(document.bill_id) from exc
        self._db.refresh(orm)
        return self._to_entity(orm)

    def list_retryable(self, now: datetime, limit: int = 100) -> list[BillDocument]:
        rows = (
            self._db.query(BillDocumentORM)
            .filter(
                BillDocumentORM.status.in_(
                    [BILL_DOCUMENT_STATUS_PENDING, BILL_DOCUMENT_STATUS_ERROR]
                ),
                or_(
                    BillDocumentORM.next_retry_at.is_(None),
                    BillDocumentORM.next_retry_at <= now,
                ),
            )
            .order_by(BillDocumentORM.uploaded_at.asc())
            .limit(limit)
            .all()
        )
        return [self._to_entity(orm) for orm in rows]

    @staticmethod
    def _to_entity(orm: BillDocumentORM) -> BillDocument:
        return BillDocument(
            id=orm.id,
            bill_id=orm.bill_id,
            filename=orm.filename,
            nas_path=orm.nas_path,
            content_type=orm.content_type,
            size_bytes=orm.size_bytes,
            uploaded_by=orm.uploaded_by,
            uploaded_at=orm.uploaded_at,
            status=orm.status,
            operation=orm.operation,
            attempts=orm.attempts,
            last_error=orm.last_error,
            next_retry_at=orm.next_retry_at,
            completed_at=orm.completed_at,
            previous_nas_path=orm.previous_nas_path,
        )
