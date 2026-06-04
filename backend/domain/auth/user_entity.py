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
    """Usuario del sistema."""

    username: str
    name: str
    role: Role
    lastname: str | None = None
    password: str | None = None
    id: int | None = None
    email: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
