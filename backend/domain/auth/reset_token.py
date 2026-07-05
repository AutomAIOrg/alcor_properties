"""
Token de restablecimiento de contraseña emitido por el sistema.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IssuedResetToken:
    """Token JWT de restablecimiento y su identificador de un solo uso."""

    token: str
    jti: str
