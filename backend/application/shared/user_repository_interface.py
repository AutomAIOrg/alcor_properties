"""
Interfaz abstracta de repositorio para usuarios.
"""

from abc import ABC, abstractmethod

from domain.auth.user_entity import NewUser, User


class IUserRepository(ABC):
    """Puerto para consultar usuarios desde la capa de aplicación."""

    @abstractmethod
    def get_by_username(self, username: str) -> User | None:
        """Devuelve el usuario asociado al username"""
        pass

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        """Devuelve el usuario asociado al id"""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """Devuelve el usuario asociado al email"""
        pass

    @abstractmethod
    def create_user(self, user: NewUser) -> User:
        """Crea un nuevo usuario."""
        pass

    @abstractmethod
    def delete_user(self, user_id: int):
        """Elimina un usuario."""
        pass

    @abstractmethod
    def update_user(self, user: User):
        """Actualiza un usuario."""
        pass

    @abstractmethod
    def get_all_users(self) -> list[User]:
        """Devuelve todos los usuarios."""
        pass
