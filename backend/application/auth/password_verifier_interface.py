from abc import ABC, abstractmethod


class IPasswordVerifier(ABC):
    """Puerto para validar una contraseña contra la persistida."""

    @abstractmethod
    def verify(self, plain_password: str, stored_password: str) -> bool:
        """Valida la contraseña recibida contra la persistida."""
        pass
