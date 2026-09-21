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

    @abstractmethod
    def set_password_reset_jti(self, user_id: int, jti: str) -> None:
        """Registra el jti del token de restablecimiento activo para el usuario."""
        pass

    @abstractmethod
    def consume_password_reset_jti(self, user_id: int, jti: str) -> bool:
        """Consume el jti de forma atómica. Devuelve True si era válido y no estaba usado."""
        pass

    @abstractmethod
    def bump_token_version(self, user_id: int) -> None:
        """Incrementa la versión de token del usuario, invalidando sus sesiones activas."""
        pass

    @abstractmethod
    def create_auth_session(
        self, user_id: int, session_id: str, jti: str, expires_at, token_version: int
    ) -> None:
        """Create a family only while the authenticated user version is still current."""

    @abstractmethod
    def rotate_auth_session(
        self,
        user_id: int,
        session_id: str,
        expected_jti: str,
        new_jti: str,
        expires_at,
        token_version: int,
    ) -> bool:
        """Rotate under a lock; persist family revocation before returning False on reuse."""

    @abstractmethod
    def is_auth_session_active(self, user_id: int, session_id: str) -> bool:
        """Check family revocation for each protected request."""
