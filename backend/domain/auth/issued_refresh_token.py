"""
Token de refresh emitido, con su identificador único (jti).
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IssuedRefreshToken:
    """Refresh token firmado junto con el jti embebido en el JWT."""

    token: str
    jti: str
    expires_at: datetime | None = None
