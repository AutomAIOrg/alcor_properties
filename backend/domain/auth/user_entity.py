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

    id: int
    username: str
    password: str
    name: str
    lastname: str
    email: str
    role: Role
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
