"""
Modelo ORM de SQLAlchemy para la tabla 'Apartamentos'.

Mapea los nombres de columnas heredados en español a nombres de atributos limpios en Python.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class ApartmentORM(Base):
    __tablename__ = "Apartamentos"

    # Clave primaria
    apartment_id: Mapped[str] = mapped_column("Booking ID", String(255), primary_key=True)

    # Características del apartamento
    community: Mapped[str | None] = mapped_column("Comunidad", String(25), nullable=True)
    apartment_description: Mapped[str | None] = mapped_column(
        "Booking Name", String(255), nullable=True
    )
    address: Mapped[str | None] = mapped_column("Direccion", String(255), nullable=True)
    rooms: Mapped[int] = mapped_column("Nº Habitaciones", Integer, nullable=False, default=0)
    bathrooms: Mapped[int] = mapped_column("Nº Banos", Integer, nullable=False, default=0)
    parking: Mapped[str] = mapped_column("Nº Parking", String(10), nullable=False, default="N/A")
    total_occupants: Mapped[int] = mapped_column(
        "Ocupacion Total", Integer, nullable=False, default=0
    )

    # Contacto del propietario
    owner_name: Mapped[str | None] = mapped_column("Owner Name", String(50), nullable=True)
    email: Mapped[str | None] = mapped_column("Email", String(35), nullable=True)
    phone: Mapped[str | None] = mapped_column("Nº Telefono", String(15), nullable=True)

    # Presentación: color personalizado en el calendario (#RRGGBB); NULL = color automático
    color: Mapped[str | None] = mapped_column("Color", String(7), nullable=True)
