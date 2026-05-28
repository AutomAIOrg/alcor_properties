from passlib.context import CryptContext
from passlib.exc import UnknownHashError

from application.auth.password_verifier_interface import IPasswordVerifier


class PasslibPasswordVerifier(IPasswordVerifier):
    """Implementación de IPasswordVerifier usando Passlib."""

    def __init__(self) -> None:
        self._pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify(self, plain_password: str, stored_password: str) -> bool:
        """Valida la contraseña recibida contra la persistida."""
        try:
            return bool(self._pwd_context.verify(plain_password, stored_password))
        except UnknownHashError:
            return False
