"""
Modelo ORM de SQLAlchemy para la tabla 'bill_documents'.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class BillDocumentORM(Base):
    __tablename__ = "bill_documents"
    __table_args__ = (UniqueConstraint("Bill ID", name="uq_bill_documents_bill_id"),)

    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(
        "Bill ID", Integer, ForeignKey("bills.ID", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column("Filename", String(255), nullable=False)
    nas_path: Mapped[str] = mapped_column("NAS Path", String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(
        "Content Type", String(100), nullable=False, default="application/pdf"
    )
    size_bytes: Mapped[int] = mapped_column("Size Bytes", Integer, nullable=False)
    uploaded_by: Mapped[int] = mapped_column(
        "Uploaded By", Integer, ForeignKey("users.ID"), nullable=False
    )
    uploaded_at: Mapped[datetime] = mapped_column("Uploaded At", DateTime, nullable=False)
