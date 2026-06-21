"""
Modelo ORM de SQLAlchemy para la tabla 'app_settings'.

Almacén clave-valor de configuración editable en caliente (p. ej., el precio por
hora de limpieza). Permite cambiar parámetros del sistema sin redeploy.
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class AppSettingORM(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column("Setting Key", String(100), primary_key=True)
    value: Mapped[str] = mapped_column("Setting Value", String(255), nullable=False)
