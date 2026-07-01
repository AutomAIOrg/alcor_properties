"""
Modelo ORM de SQLAlchemy para la tabla 'bills'.

Una factura representa la limpieza realizada en un apartamento tras una reserva.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class BillORM(Base):
    __tablename__ = "bills"

    # Clave primaria
    bill_id: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)

    # Reserva asociada
    record_id: Mapped[int | None] = mapped_column(
        "Record ID", Integer, ForeignKey("bookings.ID"), nullable=True, unique=True
    )

    # Datos de la factura
    cleaning_date: Mapped[date | None] = mapped_column("Created At", Date, nullable=True)
    clean_hours: Mapped[Decimal] = mapped_column(
        "Clean Hours", Numeric(4, 2), nullable=False, default=0
    )
    cost: Mapped[Decimal | None] = mapped_column("Cost", Numeric(10, 2), nullable=True)
    hourly_rate: Mapped[Decimal | None] = mapped_column(
        "Hourly Rate", Numeric(10, 2), nullable=True
    )

    # Apartamento limpiado
    apartment_id: Mapped[str] = mapped_column(
        "Apartment ID", String(255), ForeignKey("Apartamentos.Booking ID"), nullable=False
    )

    # Estado
    state: Mapped[str] = mapped_column("State", String(100), nullable=False, default="Creada")

    # Fecha de pago (solo cuando el estado es "Pagada")
    paid_at: Mapped[date | None] = mapped_column("Paid At", Date, nullable=True)
