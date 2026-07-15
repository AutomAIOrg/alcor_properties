"""
Entidad de dominio de usuario.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Role(Enum):
    """Roles del sistema."""

    ADMIN = "admin"
    LIMPIADORA = "limpiadora"


@dataclass
class User:
    """Usuario persistido del sistema."""

    id: int
    username: str
    password: str
    name: str
    role: Role
    lastname: str | None = None
    email: str | None = None
    token_version: int = 0
    # Mientras sea True el usuario solo puede fijar una contraseña propia: aún
    # tiene la contraseña inicial del sistema (alta o restablecimiento del admin).
    must_change_password: bool = False
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class NewUser:
    """Nuevo usuario a persistir en el sistema."""

    username: str
    password: str
    name: str
    role: Role
    lastname: str | None = None
    email: str | None = None
    must_change_password: bool = False
