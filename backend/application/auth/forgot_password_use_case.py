"""
Caso de uso para iniciar el restablecimiento de contraseña.

Si el email pertenece a un usuario existente, emite un token de restablecimiento
de un solo uso (corta duración) y envía por correo un enlace para fijar una nueva
contraseña. La respuesta es siempre la misma exista o no el email, para no revelar
qué direcciones están registradas (evita la enumeración de usuarios).
"""

import logging

from application.auth.token_manager_interface import ITokenManager
from application.shared.email_sender_interface import IEmailSender
from application.shared.user_repository_interface import IUserRepository

logger = logging.getLogger(__name__)


class ForgotPasswordUseCase:
    """Verifica el email y envía un enlace para restablecer la contraseña."""

    def __init__(
        self,
        user_repository: IUserRepository,
        token_manager: ITokenManager,
        email_sender: IEmailSender,
        frontend_url: str,
    ) -> None:
        self._user_repository = user_repository
        self._token_manager = token_manager
        self._email_sender = email_sender
        self._frontend_url = frontend_url

    def execute(self, email: str) -> None:
        user = self._user_repository.get_by_email(email)

        # Respuesta uniforme: nunca se revela si el email existe.
        if user is None:
            logger.info("Solicitud de restablecimiento para un email no registrado")
            return

        reset_token = self._token_manager.create_reset_token(subject=str(user.id))
        reset_link = f"{self._frontend_url.rstrip('/')}/reset-password?token={reset_token}"

        # Un fallo de envío (SMTP mal configurado, caído, etc.) no debe tumbar la
        # petición ni revelar nada: se registra en el log y se responde igual.
        try:
            self._email_sender.send_password_reset(user.email or email, reset_link)
            logger.info("Enlace de restablecimiento enviado a un usuario existente")
        except Exception:
            logger.exception("No se pudo enviar el email de restablecimiento")
