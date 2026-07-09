"""
Implementación de IBillDocumentRepository usando SQLAlchemy.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from domain.bills.bill_document import BillDocument
from domain.bills.bill_document_repository import IBillDocumentRepository
from domain.exceptions import BillDocumentAlreadyExistsError
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
        )
