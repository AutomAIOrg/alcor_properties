"""
Interfaz abstracta de manager para tokens de autenticación.
"""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any

from domain.auth.token_payload_entity import TokenPayload


class ITokenManager(ABC):
    """Puerto para la creación y validación de tokens de acceso y refresh."""

    @abstractmethod
    def create_access_token(
        self,
        subject: str,
        claims: Mapping[str, Any] | None = None,
    ) -> str:
        """Crea un token de acceso para un sujeto autenticado."""
        pass

    @abstractmethod
    def decode_access_token(self, token: str) -> TokenPayload:
        """Valida un token de acceso y devuelve sus claims normalizados."""
        pass

    @abstractmethod
    def create_refresh_token(self, subject: str) -> str:
        """Crea un token de refresh para un sujeto autenticado."""
        pass

    @abstractmethod
    def decode_refresh_token(self, token: str) -> TokenPayload:
        """Valida un token de refresh y devuelve sus claims normalizados."""
        pass

    @abstractmethod
    def create_reset_token(self, subject: str) -> str:
        """Crea un token de un solo uso para restablecer la contraseña."""
        pass

    @abstractmethod
    def decode_reset_token(self, token: str) -> TokenPayload:
        """Valida un token de restablecimiento de contraseña y devuelve sus claims."""
        pass
