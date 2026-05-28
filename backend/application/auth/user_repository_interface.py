"""
Interfaz abstracta de repositorio para usuarios.
"""

from abc import ABC, abstractmethod

from domain.auth.user_entity import User


class IUserRepository(ABC):
    """Puerto para consultar usuarios desde la capa de aplicación."""

    @abstractmethod
    def get_by_username(self, username: str) -> User | None:
        """Devuelve el usuario asociado al username, o None si no existe."""
        pass

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Devuelve el usuario asociado al id, o None si no existe."""
        pass
