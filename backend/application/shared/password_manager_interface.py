from abc import ABC, abstractmethod


class IPasswordManager(ABC):
    """Puerto para manejar contraseñas."""

    @abstractmethod
    def hash(self, password: str) -> str:
        """Hashea una contraseña."""
        pass

    @abstractmethod
    def verify(self, plain_password: str, stored_password: str) -> bool:
        """Valida una contraseña contra su hash almacenado."""
        pass
