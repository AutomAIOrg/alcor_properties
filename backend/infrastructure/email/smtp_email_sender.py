"""
Implementaciones de IEmailSender.

- SMTPEmailSender: envío real a través de un servidor SMTP (smtplib).
- ConsoleEmailSender: fallback de desarrollo que registra el enlace por log
  (no se envía nada). Se usa cuando no hay SMTP configurado.
"""

import logging
import smtplib
from email.message import EmailMessage

from application.shared.email_sender_interface import IEmailSender

logger = logging.getLogger(__name__)

_SUBJECT = "Restablece tu contraseña — Alcor Properties"


def _build_message(sender: str, to_email: str, reset_link: str) -> EmailMessage:
    """Construye el email de restablecimiento (texto plano + HTML)."""
    message = EmailMessage()
    message["Subject"] = _SUBJECT
    message["From"] = sender
    message["To"] = to_email
    message.set_content(
        "Has solicitado restablecer tu contraseña.\n\n"
        f"Abre este enlace para elegir una nueva (caduca en 15 minutos):\n{reset_link}\n\n"
        "Si no has sido tú, ignora este mensaje."
    )
    message.add_alternative(
        f"""\
<html>
  <body style="font-family: Arial, sans-serif; color: #333;">
    <p>Has solicitado restablecer tu contraseña.</p>
    <p>
      <a href="{reset_link}"
         style="display:inline-block;padding:10px 18px;background:#1a73e8;color:#fff;
                text-decoration:none;border-radius:6px;">
        Restablecer contraseña
      </a>
    </p>
    <p style="color:#777;font-size:13px;">
      El enlace caduca en 15 minutos. Si no has sido tú, ignora este mensaje.
    </p>
  </body>
</html>""",
        subtype="html",
    )
    return message


class SMTPEmailSender(IEmailSender):
    """Envía correos a través de un servidor SMTP estándar."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        sender: str,
        use_tls: bool = True,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._sender = sender or username
        self._use_tls = use_tls

    def send_password_reset(self, to_email: str, reset_link: str) -> None:
        message = _build_message(self._sender, to_email, reset_link)
        with smtplib.SMTP(self._host, self._port) as server:
            if self._use_tls:
                server.starttls()
            if self._username:
                server.login(self._username, self._password)
            server.send_message(message)
        logger.info("Email de restablecimiento de contraseña enviado")


class ConsoleEmailSender(IEmailSender):
    """Fallback de desarrollo: registra el enlace por log en lugar de enviar el email."""

    def send_password_reset(self, to_email: str, reset_link: str) -> None:
        logger.warning(
            "SMTP no configurado — enlace de restablecimiento (solo dev) para %s: %s",
            to_email,
            reset_link,
        )
