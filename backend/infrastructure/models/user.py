"""
Modelo ORM de SQLAlchemy para la tabla 'users'.

Mapea los nombres de columnas heredados en español a nombres de atributos limpios en Python.
"""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class UserORM(Base):
    __tablename__ = "users"

    # Clave primaria
    id: Mapped[int] = mapped_column("ID", Integer, primary_key=True, autoincrement=True)

    # Identificación del usuario
    username: Mapped[str] = mapped_column("Username", String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column("Password", String(255), nullable=False)
    name: Mapped[str] = mapped_column("Name", String(255), nullable=False)
    lastname: Mapped[str | None] = mapped_column("Lastname", String(255), nullable=True)
    email: Mapped[str | None] = mapped_column("Email", String(255), nullable=True, unique=True)

    # Rol
    role: Mapped[str] = mapped_column("Role", String(100), nullable=False)

    # Token de restablecimiento de contraseña activo (jti del JWT, un solo uso).
    password_reset_jti: Mapped[str | None] = mapped_column(
        "PasswordResetJti", String(36), nullable=True
    )

    # Versión de token de sesión. Al incrementarse invalida los access/refresh previos.
    token_version: Mapped[int] = mapped_column(
        "TokenVersion", Integer, nullable=False, default=0, server_default="0"
    )
