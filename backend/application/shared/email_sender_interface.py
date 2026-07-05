"""
Interfaz abstracta para el envío de emails.
"""

from abc import ABC, abstractmethod


class IEmailSender(ABC):
    """Puerto para el envío de correos electrónicos desde la capa de aplicación."""

    @abstractmethod
    def send_password_reset(self, to_email: str, reset_link: str) -> None:
        """Envía al usuario el enlace para restablecer su contraseña."""
        pass
