"""
Modelo ORM de SQLAlchemy para la tabla 'bookings'.

Mapea los nombres de columnas heredados en español a nombres de atributos limpios en Python.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class BookingORM(Base):
    __tablename__ = "bookings"

    # Clave primaria
    record_id: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)

    # Identificación de la reserva
    booking_id: Mapped[str] = mapped_column("Booking ID", String(255), nullable=False)
    booking_number: Mapped[Optional[str]] = mapped_column("Nº Booking", String(255), nullable=True)

    # Huésped
    guest_name: Mapped[Optional[str]] = mapped_column("Nombre,Apellidos", String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column("Email", String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column("Movil", String(100), nullable=True)

    # Estancia
    check_in: Mapped[date] = mapped_column("Check-In", Date, nullable=False)
    check_out: Mapped[date] = mapped_column("Check-Out", Date, nullable=False)
    nights: Mapped[Optional[int]] = mapped_column("Nº Noches", Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column("Status", String(100), nullable=True)

    # Ocupación
    persons: Mapped[Optional[int]] = mapped_column("Nº Personas", Integer, nullable=True)
    adults: Mapped[Optional[int]] = mapped_column("Nº Adultos", Integer, nullable=True)
    children: Mapped[Optional[int]] = mapped_column("Nº Niños", Integer, nullable=True)

    # Financiero
    price: Mapped[Optional[Decimal]] = mapped_column("Precio", Numeric(10, 2), nullable=True)
    charges: Mapped[Optional[Decimal]] = mapped_column("Comm y Cargos", Numeric(10, 2), nullable=True)

    # Notas
    notes: Mapped[Optional[str]] = mapped_column("Notes", Text, nullable=True)
