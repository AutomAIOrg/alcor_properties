"""
Modelo ORM de SQLAlchemy para la tabla 'bills'.

Una factura representa la limpieza realizada en un apartamento tras una reserva.
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
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

    # Tipo de limpieza aplicado (catálogo). El nombre se congela como snapshot para
    # preservar el histórico aunque el tipo se edite o elimine posteriormente. Por eso
    # la FK usa ON DELETE SET NULL: al borrar un tipo la factura conserva el nombre
    # congelado y solo pierde la referencia viva.
    cleaning_type_id: Mapped[int | None] = mapped_column(
        "Cleaning Type ID",
        Integer,
        ForeignKey("cleaning_types.ID", ondelete="SET NULL"),
        nullable=True,
    )
    cleaning_type_name: Mapped[str | None] = mapped_column(
        "Cleaning Type Name", String(100), nullable=True
    )

    # Apartamento limpiado
    apartment_id: Mapped[str] = mapped_column(
        "Apartment ID", String(255), ForeignKey("Apartamentos.Booking ID"), nullable=False
    )

    # Estado
    state: Mapped[str] = mapped_column("State", String(100), nullable=False, default="Creada")

    # Fecha de pago declarada por la limpiadora al confirmar (puede constar ya con la
    # factura aún en "Creada", a la espera de la confirmación de administración)
    paid_at: Mapped[date | None] = mapped_column("Paid At", Date, nullable=True)

    # Confirmaciones de pago por rol. La factura solo pasa a "Pagada" cuando ambas
    # partes (administración y limpiadora) han confirmado; cada columna guarda el
    # instante exacto (fecha + hora) en que esa parte confirmó, junto con el nombre
    # completo de quien confirmó (congelado, como snapshot histórico) para mostrar
    # "Pago confirmado por <Nombre Apellidos> el día <fecha> a las <hora>".
    paid_confirmed_by_admin: Mapped[datetime | None] = mapped_column(
        "Paid Confirmed By Admin", DateTime, nullable=True
    )
    paid_confirmed_by_admin_name: Mapped[str | None] = mapped_column(
        "Paid Confirmed By Admin Name", String(200), nullable=True
    )
    paid_confirmed_by_cleaner: Mapped[datetime | None] = mapped_column(
        "Paid Confirmed By Cleaner", DateTime, nullable=True
    )
    paid_confirmed_by_cleaner_name: Mapped[str | None] = mapped_column(
        "Paid Confirmed By Cleaner Name", String(200), nullable=True
    )

    # Nota explicativa (solo cuando el estado es "Cancelada")
    cancellation_note: Mapped[str | None] = mapped_column(
        "Cancellation Note", String(500), nullable=True
    )

    # Fecha de generación de la factura (congelada). El nombre físico evita colisión
    # con la columna heredada "Created At", que en realidad almacena cleaning_date.
    created_at: Mapped[date | None] = mapped_column("Bill Created At", Date, nullable=True)
