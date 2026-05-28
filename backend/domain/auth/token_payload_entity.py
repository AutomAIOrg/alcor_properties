"""
Entidad de dominio para el token de acceso.
"""

from dataclasses import dataclass
from datetime import datetime

from domain.auth.user_entity import Role


@dataclass(frozen=True)
class TokenPayload:
    """Claims ya validados de un token de acceso."""

    subject: str
    expires_at: datetime
    issued_at: datetime | None = None
    username: str | None = None
    role: Role | None = None
