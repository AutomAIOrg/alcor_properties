from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from application.shared.password_manager_interface import IPasswordManager


class PasslibPasswordManager(IPasswordManager):
    """Implementación de IPasswordManager para manejar contraseñas usando Passlib."""

    def __init__(self) -> None:
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash(self, password: str) -> str:
        """Hashea una contraseña."""
        return self._pwd_context.hash(password)

    def verify(self, plain_password: str, stored_password: str) -> bool:
        """Valida la contraseña recibida contra su hash almacenado."""
        try:
            return bool(self._pwd_context.verify(plain_password, stored_password))
        except UnknownHashError:
            return False
