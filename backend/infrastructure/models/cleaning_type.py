"""
Modelo ORM de SQLAlchemy para la tabla 'cleaning_types'.

Un tipo de limpieza define la tarifa por hora aplicada al facturar una limpieza de
esa clase (p. ej. "Limpieza normal", "Limpieza fin de semana").
"""

from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class CleaningTypeORM(Base):
    __tablename__ = "cleaning_types"

    cleaning_type_id: Mapped[int] = mapped_column(
        "ID", Integer, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column("Name", String(100), nullable=False, unique=True)
    hourly_rate: Mapped[Decimal] = mapped_column("Hourly Rate", Numeric(10, 2), nullable=False)
    active: Mapped[bool] = mapped_column("Active", Boolean, nullable=False, default=True)
